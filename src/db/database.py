import os
import pyodbc
import logging
import json
from .utils import Buffer, VectorSet, NpEncoder, DataSourceConfig

_logger = logging.getLogger("uvicorn")

class DatabaseEngineException(Exception):
    pass

class DatabaseEngine:
    def __init__(self) -> None:
        self._connection_string = os.environ["MSSQL"]
        self._index_id = None
       
    def from_config(config:DataSourceConfig):
        db = DatabaseEngine()
        db._source_table_schema:str = config.source_table_schema
        db._source_table_name:str = config.source_table_name
        db._source_id_column_name:str = config.source_id_column_name
        db._source_vector_column_name:str = config.source_vector_column_name
        db._vector_dimensions:str = config.vector_dimensions             
        db.initialize_internal_variables()
        db.validate_database_objects()
        return db

    def from_id(id:int):
        db = DatabaseEngine()
        conn = pyodbc.connect(db._connection_string) 

        cursor = conn.cursor()  
        cursor.execute("""
            select 
                parsename(source_table_name, 2) as source_schema_name,
                parsename(source_table_name, 1) as source_table_name,
                id_column_name,
                vector_column_name,
                dimensions_count as vector_dimensions
            from 
                [$vector].[kmeans] 
            where 
                id = ?
            and
                status = 'CREATED';""", id)
        row = cursor.fetchone()

        if (row == None):
            raise DatabaseEngineException(f"Index #{id} not found.")

        db._source_table_schema = str(row.source_schema_name)
        db._source_table_name = str(row.source_table_name)
        db._source_id_column_name = str(row.id_column_name)
        db._source_vector_column_name = str(row.vector_column_name)
        db._vector_dimensions = int(row.vector_dimensions)
        cursor.close()
        conn.close()
        
        db.initialize_internal_variables()
        db.validate_database_objects()

        return db

    def validate_config(self):
        c = {
            "table_schema": self._source_table_schema,
            "table_name": self._source_table_name,
            "id_column_name": self._source_id_column_name,
            "vector_column_name": self._source_vector_column_name,
            "vector_dimensions": self._vector_dimensions
        }

        _logger.info(f"Configuration: {json.dumps(c)}...")

        if (self._source_table_schema == None):
            raise DatabaseEngineException("Source table schema not defined.")
        
        if (self._source_table_name == None):
            raise DatabaseEngineException("Source table name not defined.")
    
        if (self._source_vector_column_name == None):
            raise DatabaseEngineException("Source vector column not defined.")
    
        if (self._source_id_column_name == None):
            raise DatabaseEngineException("Source id column not defined.")
    
        if (self._vector_dimensions == None):
            raise DatabaseEngineException("Expected number of dimensions for vector column not define.")    

    def initialize_internal_variables(self):    
        self.validate_config()
        self._source_table_fqname = f'[{self._source_table_schema}].[{self._source_table_name}]'
        self._target_table_name = f'{self._source_table_name}${self._source_vector_column_name}'
        self._function1_fqname=f'[$vector].[find_similar${self._target_table_name}]'
        self._function2_fqname=f'[$vector].[find_cluster${self._target_table_name}]'
        self._embeddings_table_fqname = f'[{self._source_table_schema}].[{self._target_table_name}]'
        self._clusters_centroids_table_fqname = f'[$vector].[{self._target_table_name}$clusters_centroids]'
        self._clusters_centroids_tmp_table_fqname = f'[$tmp].[{self._target_table_name}$clusters_centroids]'
        self._clusters_table_fqname = f'[$vector].[{self._target_table_name}$clusters]'  
        self._clusters_tmp_table_fqname = f'[$tmp].[{self._target_table_name}$clusters]'  

    def validate_database_objects(self):
        conn = pyodbc.connect(self._connection_string) 
        
        table_id = conn.execute("select object_id(?)", self._source_table_fqname).fetchval()
        if (table_id == None):
            raise DatabaseEngineException(f"Source table {self._source_table_fqname} not found.")
        
        column_id_id = conn.execute("select [column_id] from sys.columns where [object_id] = ? and [name] = ?", table_id, self._source_id_column_name).fetchval()
        if (column_id_id == None):
            raise DatabaseEngineException(f"Source table column {self._source_id_column_name} not found.")

        column_vector_id = conn.execute("select [column_id] from sys.columns where [object_id] = ? and [name] = ?", table_id, self._source_vector_column_name).fetchval()
        if (column_vector_id == None):
            raise DatabaseEngineException(f"Source table column {self._source_vector_column_name} not found.")
        
        conn.close()

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
                        [dimensions_count] int null,
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
    
    def create_index_metadata(self, force: bool) -> int:
        id = None
        conn = pyodbc.connect(self._connection_string) 

        try:
            cursor = conn.cursor()  
            
            id = cursor.execute("""
                select id from [$vector].[kmeans] where [source_table_name] = ? and [vector_column_name] = ?;
                """,
                self._source_table_fqname,
                self._source_vector_column_name
            ).fetchval()
            if (id != None):
                if (force == False):
                    raise DatabaseEngineException(f"Index for {self._source_table_fqname}.{self._source_vector_column_name} already exists.")
                else:
                    _logger.info(f"Index creation forced over existing index {id}...")
            
            if (id == None):
                _logger.info(f"Registering new index...")
                id = cursor.execute("""
                    set nocount on;
                    insert into [$vector].[kmeans] 
                        ([source_table_name], [id_column_name], [vector_column_name], [dimensions_count], [status], [updated_on])
                    values
                        (?, ?, ?, ?, 'INITIALIZING', sysdatetime());
                    select scope_identity() as id;
                    """,
                    self._source_table_fqname,
                    self._source_id_column_name,
                    self._source_vector_column_name,
                    self._vector_dimensions  
                ).fetchval()
            else:
                _logger.info(f"Updating existing index...")
                cursor.execute("""
                    update 
                        [$vector].[kmeans] 
                    set
                        [status] = 'INITIALIZING',
                        [item_count] = null,                            
                        [updated_on] = sysdatetime()
                    where 
                        id = ?;
                    """,
                    id
                )

            cursor.commit()
        finally:
            conn.close()
        
        self._index_id = id
        return id
    
    def update_index_metadata(self, status:str):
        conn = pyodbc.connect(self._connection_string) 

        cursor = conn.cursor()  
        cursor.execute("""
            update 
                [$vector].[kmeans] 
            set                
                [status] = ?                
            where 
                id = ?;""", 
            status, 
            self._index_id, 
            )
        conn.commit()

        cursor.close()
        conn.close()

    def finalize_index_metadata(self, vectors_count:int):
        conn = pyodbc.connect(self._connection_string) 

        cursor = conn.cursor()  
        cursor.execute("""
            update 
                [$vector].[kmeans] 
            set
                [item_count] = ?,
                [dimensions_count] = ?,
                [status] = 'CREATED',                
                [updated_on] = sysdatetime()
            where 
                id = ?;""", 
            vectors_count, 
            self._vector_dimensions,
            self._index_id, 
            )
        conn.commit()

        cursor.close()
        conn.close()
  
    def load_vectors_from_db(self):            
        query = f"""
            select {self._source_id_column_name} as item_id, {self._source_vector_column_name} as vector from {self._source_table_fqname} 
        """
        buffer = Buffer()    
        result = VectorSet(self._vector_dimensions)
        conn = pyodbc.connect(self._connection_string) 
        cursor = conn.cursor()
        cursor.execute(query)
        tr = 0
        while(True):
            buffer.clear()    
            rows = cursor.fetchmany(10000)
            if (rows == []):
                _logger.info("Done")
                break

            for idx, row in enumerate(rows):
                buffer.add(row.item_id, json.loads(row.vector))
            
            result.add(buffer)            
            tr += (idx+1)

            mf = int(result.get_memory_usage() / 1024 / 1024)
            _logger.info("Loaded {0} rows, total rows {1}, total memory footprint {2} MB".format(idx+1, tr, mf))        

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
            drop table if exists {self._clusters_centroids_tmp_table_fqname} 
            create table {self._clusters_centroids_tmp_table_fqname}
                (
                    cluster_id int not null,
                    vector_value_id int not null,
                    vector_value float not null
                )
            """)
        cursor.commit()
        cursor.executemany(f"""    
            insert into {self._clusters_centroids_tmp_table_fqname} (cluster_id, vector_value_id, vector_value) 
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
            create clustered columnstore index ixcc on {self._clusters_centroids_tmp_table_fqname} order (cluster_id, vector_value_id) with (maxdop = 1)                     
        """)
        cursor.commit()
        
        _logger.info("Switching to final centroids table...")
        cursor.execute(f"""
                       drop table if exists {self._clusters_centroids_table_fqname};
                       alter schema [$vector] transfer {self._clusters_centroids_tmp_table_fqname};
                       """)
        cursor.commit()

        cursor.close()        
        conn.close()
       
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
            if object_id('{self._clusters_table_fqname}') is null begin
                create table {self._clusters_table_fqname} (
                    cluster_id int not null,
                    item_id int not null        
                )
            end   
            drop table if exists {self._clusters_tmp_table_fqname} 
            create table {self._clusters_tmp_table_fqname}
                (
                    cluster_id int not null,
                    item_id int not null    
                )                        
        """)        
        cursor.executemany(f"insert into {self._clusters_tmp_table_fqname} (item_id, cluster_id) values (?, ?)", params)
        cursor.commit()

        _logger.info("Creating index...")
        cursor.execute(f"create clustered index ixc on {self._clusters_table_fqname} (item_id, cluster_id)")
        cursor.commit()
        
        _logger.info("Switching to final centroids elements table...")
        cursor.execute(f"""
                       drop table if exists {self._clusters_table_fqname};
                       alter schema [$vector] transfer {self._clusters_tmp_table_fqname};
                       """)
        cursor.commit()

        cursor.close()
        conn.commit()        
        _logger.info("Centroids elements saved.")

    def create_similarity_function(self):
        conn = pyodbc.connect(self._connection_string)         
        cursor = conn.cursor()  
        
        _logger.info(f"Creating function {self._function1_fqname}...")
        cursor = conn.cursor()
        cursor.execute(f"""
        create or alter function {self._function1_fqname} (@vector nvarchar(max), @probe int, @similarity float)
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
                sum(v1.[vector_value] * v2.[vector_value]) as dot_product              
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
                c.cluster_id in (select top(@probe) cluster_id from cteCentroids order by dot_product desc)
        ), 
        cteIds as 
        (
            select
                v2.id, 
                sum(v1.[vector_value] * v2.[vector_value]) as dot_product              
            from 
                cteVectorInput v1
            inner join 
                cteVectorContent v2 on v1.vector_value_id = v2.vector_value_id
            group by
                v2.id
        )
        select
            a.*, c.dot_product
        from
            cteIds c
        inner join  
            {self._source_table_fqname} a on c.id = a.id
        where 
            dot_product > @similarity;
        """)
        cursor.close()
        conn.commit()
        _logger.info(f"Function created.")

    def create_find_cluster_function(self):
        conn = pyodbc.connect(self._connection_string)         
        cursor = conn.cursor()  
        
        _logger.info(f"Creating function {self._function2_fqname}...")
        cursor = conn.cursor()
        cursor.execute(f"""
        create or alter function {self._function2_fqname} (@vector nvarchar(max))
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
                sum(v1.[vector_value] * v2.[vector_value]) as dot_product              
            from 
                cteVectorInput v1
            inner join 
                {self._clusters_centroids_table_fqname} v2 on v1.vector_value_id = v2.vector_value_id
            group by
                v2.cluster_id
        )
        select top(1)
            cluster_id
        from
            cteCentroids c        
        order by
            dot_product desc
        """)
        cursor.close()
        conn.commit()
        _logger.info(f"Function created.")