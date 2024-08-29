/*
** Make sure to run the script in the `vectordb` database **
*/

/*
    As an example take an existing value to simulate a new item to be added
*/
declare @id int = 99999;
declare @v nvarchar(max);
select @v = content_vector from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov';

set xact_abort on
begin tran

/*
    Insert new element into source table
*/
insert into dbo.wikipedia_articles_embeddings
    (id, [url], title, [text], title_vector, content_vector, vector_id)
select 
    @id, 'uri://sample', 'Isaac Asimov Copy', 'sample content', '[]' as title_vector, @v as content_vector, @id

/*
    Insert vector
*/
insert into 
    [dbo].[wikipedia_articles_embeddings$content_vector]
select
    @id, vector_value_id, vector_value
from (
    select 
        cast([key] as smallint) as vector_value_id, 
        cast([value] as float) as vector_value
    from
        openjson(@v) as t
    ) v
;

/*
    Add vector to cluster
*/
declare @c int;
select top(1) @c = cluster_id from [$vector].[find_cluster$wikipedia_articles_embeddings$content_vector](@v)
insert into 
    [$vector].[wikipedia_articles_embeddings$content_vector$clusters] (cluster_id, item_id) 
values 
    (@c, @id);
    
commit tran

