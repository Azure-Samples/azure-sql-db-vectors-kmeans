/*
    Extract vectors values as descrived in https://github.com/Azure-Samples/azure-sql-db-openai
*/
select 
    id as item_id,
    cast([key] as int) as [vector_value_id],
    cast([value] as float) as [vector_value]
into 
    [dbo].[wikipedia_articles_embeddings$content_vector]
from
    [dbo].[wikipedia_articles_embeddings]
cross apply
    openjson([content_vector])    
go

/*
    Create clustered columnstore index
*/
create clustered columnstore index ixcc on [dbo].[wikipedia_articles_embeddings$content_vector] order (item_id, vector_value_id) with (maxdop = 1)        
go