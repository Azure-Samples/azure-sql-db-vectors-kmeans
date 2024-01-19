import os
import pyodbc
import logging
import json
from .utils import Buffer, VectorSet, NpEncoder, DataSourceConfig

_logger = logging.getLogger("uvicorn")

class DatabaseEngine:

    def __init__(self, config:DataSourceConfig) -> None:
        self._connection_string = os.environ["MSSQL"]
        self._index_id = None
        self._source_table_schema = config.source_table_schema
        self._source_table_name = config.source_table_name
        self._source_id_column_name = config.source_id_column_name
        self._source_vector_column_name = config.source_vector_column_name
        self._vector_dimensions = config.vector_dimensions
        self._source_table_fqname = f'[{self._source_table_schema}].[{self._source_table_name}]'
        self._target_table_name = f'{self._source_table_name}${self._source_vector_column_name}'
        self._function_fqname=f'[$vector].[find_similar${self._target_table_name}]'
        self._embeddings_table_fqname = f'[$vector].[{self._target_table_name}]'
        self._clusters_centroids_table_fqname = f'[$vector].[{self._target_table_name}$clusters_centroids]'
        self._clusters_table_fqname = f'[$vector].[{self._target_table_name}$clusters]'  

    def initialize(self): 
        conn = pyodbc.connect(self._connection_string)
        try:        
            cursor = conn.cursor()  
            cursor.execute(f"""
                if schema_id('$vector') is null begin
                    exec('create schema [$vector] authorization dbo')
                end
                if schema_id('$tmp') is null begin
                    exec('create schema [$tmp] authorization dbo')
                end           
                if object_id('[$vector].[kmeans]') is null begin
                    create table [$vector].[kmeans]
                    (
                        [id] int identity not null,
                        [source_table_name] sysname not null,
                        [id_column_name] sysname not null,
                        [vector_column_name] sysname not null,
                        [item_count] int null,
                        [status] varchar(100) not null,
                        [updated_on] datetime2 not null,
                        primary key nonclustered ([id]),
                        unique nonclustered ([source_table_name], [vector_column_name])
                    )
                end             
            """)
            cursor.close()
            conn.commit()
        finally:
            conn.close()
        
    def get_info(self):
        return {
            "id": self._index_id,
            "source":{
                "table": self._source_table_fqname,
                "vector_column": self._source_vector_column_name,
                "id_column": self._source_id_column_name
            },
            "target":{
                "vector_table": self._embeddings_table_fqname,
                "cluster_centroids_table": self._clusters_centroids_table_fqname,
                "cluster_table": self._clusters_table_fqname,
                "function": self._function_fqname
            }
        }
    
    def update_index_metadata(self, vectors_count:int):
        conn = pyodbc.connect(self._connection_string) 

        cursor = conn.cursor()  
        cursor.execute("""
            update 
                [$vector].[kmeans] 
            set
                [item_count] = ?,
                [status] = 'CREATED',
                [updated_on] = sysdatetime()
            where 
                id = ?;""", 
            vectors_count, 
            self._index_id, 
            )
        conn.commit()

        cursor.close()
        conn.close()

    def create_index_metadata(self) -> int:
        id = None
        conn = pyodbc.connect(self._connection_string) 

        try:
            cursor = conn.cursor()  
            id = cursor.execute("""
                set nocount on;
                insert into [$vector].[kmeans] 
                    ([source_table_name], [id_column_name], [vector_column_name], [status], [updated_on])
                values
                    (?, ?, ?, 'INITIALIZING', sysdatetime());
                select scope_identity() as id;
                """,
                self._source_table_fqname,
                self._source_id_column_name,
                self._source_vector_column_name  
            ).fetchval()
            cursor.close()
            conn.commit()
        finally:
            conn.close()
        
        self._index_id = id
        return id
    
    
    def load_vectors_from_db(self):    
        query = f"""
            select {self._source_id_column_name} as item_id, {self._source_vector_column_name} as vector from {self._source_table_fqname} 
        """
        buffer = Buffer()    
        result = VectorSet(self._vector_dimensions)
        conn = pyodbc.connect(self._connection_string) 
        cursor = conn.cursor()
        cursor.execute(query)
        while(True):
            buffer.clear()    
            rows = cursor.fetchmany(10000)
            if (rows == []):
                _logger.info("Done")
                break

            for idx, row in enumerate(rows):
                buffer.add(row.item_id, json.loads(row.vector))
            
            result.add(buffer)            

            mf = int(result.get_memory_usage() / 1024 / 1024)
            _logger.info("Loaded {0} rows, total memory footprint {1} MB".format(idx+1, mf))        

        cursor.close()
        conn.commit()
        conn.close()
        return result.ids, result.vectors
    
    def save_clusters_centroids(self, centroids):
        conn = pyodbc.connect(self._connection_string)         
        cursor = conn.cursor()  
        params = [(i, json.dumps(centroids[i], cls=NpEncoder)) for i in range(0, len(centroids))]
        cursor = conn.cursor()
        
        #cursor.fast_executemany = True        
        _logger.info(f"Saving centroids to {self._clusters_centroids_table_fqname}...")
        cursor.execute(f"""
            if object_id('{self._clusters_centroids_table_fqname}') is null begin
                create table {self._clusters_centroids_table_fqname}
                (
                    cluster_id int not null,
                    vector_value_id int not null,
                    vector_value float not null
                )
            end    
            """)
        cursor.commit()
        cursor.execute(f"truncate table {self._clusters_centroids_table_fqname}")
        cursor.commit()
        cursor.execute(f"drop index ixcc on {self._clusters_centroids_table_fqname}")
        cursor.commit()
        cursor.executemany(f"""    
            insert into {self._clusters_centroids_table_fqname} (cluster_id, vector_value_id, vector_value) 
            select 
                id as cluster_id,
                cast([key] as int) as [vector_value_id],
                cast([value] as float) as [vector_value]
            from
                (values (?, ?)) T(id, vector)
            cross apply
                openjson([vector])    
            """, 
            params)
        _logger.info("Creating columnstore index...")
        cursor.execute(f"""
            create clustered columnstore index ixcc on {self._clusters_centroids_table_fqname} order (cluster_id, vector_value_id) with (maxdop = 1)                     
        """)
        cursor.commit()
        cursor.close()
        conn.close()
        _logger.info("Columnstore index created.")
        _logger.info("Centroids saved.")

    def save_clusters_items(self, ids, labels):
        clustered_ids = dict(zip(ids, labels))
        params = [(int(ids[i]), int(labels[i])) for i in range(0, len(clustered_ids))]

        conn = pyodbc.connect(self._connection_string)         
        cursor = conn.cursor()  
        cursor.fast_executemany = True
        _logger.info(f"Saving centroids elements into {self._clusters_table_fqname}...")        
        cursor.execute(f"drop table if exists {self._clusters_table_fqname}")
        cursor.execute(f"""
            create table {self._clusters_table_fqname} (
                cluster_id int not null,
                item_id int not null        
            )
        """)
        cursor.executemany(f"insert into {self._clusters_table_fqname} (item_id, cluster_id) values (?, ?)", params)
        _logger.info("Creating index...")
        cursor.execute(f"create clustered index ixc on {self._clusters_table_fqname} (item_id, cluster_id)")
        cursor.close()
        conn.commit()
        _logger.info("Index created.")
        _logger.info("Centroids elements saved.")

    def create_similarity_function(self):
        conn = pyodbc.connect(self._connection_string)         
        cursor = conn.cursor()  
        
        _logger.info(f"Creating function {self._function_fqname}...")
        cursor = conn.cursor()
        cursor.execute(f"""
        create or alter function {self._function_fqname} (@vector nvarchar(max), @probe int, @similarity float)
        returns table
        as return
        with cteVectorInput as
        (
            select 
                cast([key] as smallint) as vector_value_id, 
                cast([value] as float) as vector_value
            from
                openjson(@vector) as t
        ),
        cteCentroids as
        (
            select 
                v2.cluster_id, 
                sum(v1.[vector_value] * v2.[vector_value]) as cosine_similarity              
            from 
                cteVectorInput v1
            inner join 
                {self._clusters_centroids_table_fqname} v2 on v1.vector_value_id = v2.vector_value_id
            group by
                v2.cluster_id
        ),
        cteVectorContent as
        (
            select 
                e.item_id as id,
                vector_value_id, 
                vector_value
            from 
                {self._embeddings_table_fqname} e
            inner join 
                {self._clusters_table_fqname} c on e.item_id = c.item_id
            where
                c.cluster_id in (select top(@probe) cluster_id from cteCentroids order by cosine_similarity desc)
        ), 
        cteIds as 
        (
            select
                v2.id, 
                sum(v1.[vector_value] * v2.[vector_value]) as cosine_similarity              
            from 
                cteVectorInput v1
            inner join 
                cteVectorContent v2 on v1.vector_value_id = v2.vector_value_id
            group by
                v2.id
        )
        select
            a.id, a.title, c.cosine_similarity
        from
            cteIds c
        inner join  
            {self._source_table_fqname} a on c.id = a.id
        where 
            cosine_similarity > @similarity;
        """)
        cursor.close()
        conn.commit()
        _logger.info(f"Function created.")