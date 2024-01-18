import os
import pyodbc
import logging
import json
from .utils import Buffer, VectorSet, NpEncoder

_logger = logging.getLogger("uvicorn")

class DatabaseEngine:
    def __init__(self, configuration) -> None:
        self._connection_string = os.environ["MSSQL"]
        self._index_id = configuration["ID"]
        self._configuration = configuration["DATASOURCE"]
        self._source_table_fqname = f'[{self._configuration["SCHEMA"]}].[{self._configuration["TABLE"]}]'
        self._source_id_column_name = self._configuration["COLUMN"]["ID"]
        self._source_vector_column_name = self._configuration["COLUMN"]["VECTOR"]
        self._target_table_name = f'{self._configuration["TABLE"]}${self._source_vector_column_name}'
        self._function_fqname=f'[$vector].[find_similar${self._target_table_name}]'
        self._embeddings_table_fqname = f'[$vector].[{self._target_table_name}]'
        self._clusters_centroids_table_fqname = f'[$vector].[{self._target_table_name}$clusters_centroids]'
        self._clusters_table_fqname = f'[$vector].[{self._target_table_name}$clusters]'  

    def initialize(self): 
        conn = pyodbc.connect(self._connection_string) 
        cursor = conn.cursor()  
        cursor.execute(f"""
            SELECT 1                 
        """)
        cursor.close()
        conn.commit()
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
    
    def save_index(self, index_type, index_class, index_bin, vectors_count:int, dimensions_count:int, version:int):
        conn = pyodbc.connect(self._connection_string) 

        cursor = conn.cursor()  
        cursor.execute("delete from [$vector].[index] where id = ?", self._index_id)
        conn.commit()

        cursor.execute("""
            insert into [$vector].[index] 
                ([id], [type], [class], [data], [item_count], [vector_dimensions], [data_version], [saved_on]) 
            values 
                (?, ?, ?, ?, ?, ?, ?, sysdatetime());""", 
            self._index_id, index_type, index_class, index_bin, vectors_count, dimensions_count, version)
        conn.commit()

        cursor.close()
        conn.close()

    def load_index(self):
        conn = pyodbc.connect(self._connection_string) 
        cursor = conn.cursor()  

        row = cursor.execute(f"select [data], [data_version] from [$vector].[index] where id = ?", self._index_id).fetchone()
        if row == None:
            return None, 0
        pkl = row[0]
        version = row[1]
        cursor.close()
        conn.close()

        return pkl, version
    
    def load_vectors_from_db(self):    
        #_logger.info(f"Configuration: {self._configuration}")
        conn = pyodbc.connect(self._connection_string) 
        cursor = conn.cursor()  
        current_version = cursor.execute("select change_tracking_current_version() as current_version;").fetchval() or 0
        cursor.close()

        query = f"""
            select {self._source_id_column_name} as item_id, {self._source_vector_column_name} as vector from {self._source_table_fqname} 
        """
        cursor = conn.cursor()
        cursor.execute(query)
        buffer = Buffer()    
        result = VectorSet(self._configuration["VECTOR"]["DIMENSIONS"])
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
        return current_version, result.ids, result.vectors
    
    def save_clusters_centroids(self, centroids):
        conn = pyodbc.connect(self._connection_string)         
        cursor = conn.cursor()  
        params = [(i, json.dumps(centroids[i], cls=NpEncoder)) for i in range(0, len(centroids))]
        cursor = conn.cursor()
        
        #cursor.fast_executemany = True        
        _logger.info(f"Saving centroids to {self._clusters_centroids_table_fqname}...")
        cursor.execute(f"drop table if exists {self._clusters_centroids_table_fqname}")
        cursor.execute(f"""
            create table {self._clusters_centroids_table_fqname} (
                cluster_id int not null,
                vector_value_id int not null,
                vector_value float not null
            )
        """)
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
        conn.commit()
        cursor.close()
        conn.close()
        _logger.info("Columnstore index created.")

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
        _logger.info(f"Function created...")

    def get_changes(self, from_version:int = 0):
        EMBEDDINGS = self._configuration
        query = f"""
        declare @fromVersion int = ?
        declare @reason int = 0

        declare @curVer int = change_tracking_current_version();
        declare @minVer int = change_tracking_min_valid_version(object_id('[{EMBEDDINGS["SCHEMA"]}].[{EMBEDDINGS["TABLE"]}]'));

        -- Full rebuild needed
        if (@fromVersion < @minVer) begin
            set @reason = 2
        end

        -- No Changes
        if (@fromVersion = @curVer) begin
            set @reason = 1
        end

        if (@reason > 0)
        begin
            select
                @curVer as 'Metadata.Sync.Version',
                'None' as 'Metadata.Sync.Type',
                @reason as 'Metadata.Sync.ReasonCode'        
            for
                json path, without_array_wrapper
        end else begin
            declare @result nvarchar(max) = ((
            select
                @curVer as 'Metadata.Sync.Version',
                'Diff' as 'Metadata.Sync.Type',
                @reason as 'Metadata.Sync.ReasonCode',       
                [Data] = json_query((
                    select 
                        ct.SYS_CHANGE_OPERATION as '$operation',
                        ct.SYS_CHANGE_VERSION as '$version',
                        ct.[{EMBEDDINGS['COLUMN']['ID']}] as id, 
                        t.[{EMBEDDINGS['COLUMN']['VECTOR']}] as vector
                    from 
                        [{EMBEDDINGS["SCHEMA"]}].[{EMBEDDINGS["TABLE"]}] as t 
                    right outer join 
                        changetable(changes [{EMBEDDINGS["SCHEMA"]}].[{EMBEDDINGS["TABLE"]}] , @fromVersion) as ct on ct.[{EMBEDDINGS['COLUMN']['ID']}] = t.[{EMBEDDINGS['COLUMN']['ID']}]
                    for 
                        json path
                ))
            for
                json path, without_array_wrapper
            ))
            select @result as result
        end
        """
            
        conn = pyodbc.connect(self._connection_string)     
        cursor = conn.cursor()
        #print(from_version)
        cursor.execute(query, from_version)
        result = cursor.fetchone()
        result = json.loads(result[0])
        cursor.close()
        conn.close()
        return result

