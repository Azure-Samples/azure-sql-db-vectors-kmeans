/*
** Make sure to run the script in the `vectordb` database **
*/

-- Get a sample vector 
declare @v nvarchar(max)
select @v = content_vector from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov'

-- Find in which cluster it belongs to 
select * from [$vector].[find_cluster$wikipedia_articles_embeddings$content_vector](@v)
go