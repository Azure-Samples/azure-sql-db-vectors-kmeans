/*
** Make sure to run the script in the `vectordb` database **
*/

set xact_abort on
begin tran

delete from [$vector].[wikipedia_articles_embeddings$content_vector$clusters] where item_id = 99999
delete from [dbo].[wikipedia_articles_embeddings$content_vector] where item_id = 99999
delete from [dbo].[wikipedia_articles_embeddings] where id = 99999

commit tran