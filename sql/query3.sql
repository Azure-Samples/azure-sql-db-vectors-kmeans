select 
    id, source_table_name, id_column_name, vector_column_name, 
    [type], [class], item_count, vector_dimensions, data_version, saved_on 
from 
    [$vector].[index]