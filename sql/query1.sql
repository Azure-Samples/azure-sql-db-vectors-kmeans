
set statistics time on


--- TITLE

declare @v nvarchar(max)
select @v = title_vector from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov'

select top (10) * from [$vector].find_similar$wikipedia_articles_embeddings$title_vector(@v, 1, 0.75) order by  cosine_similarity desc


declare @v nvarchar(max)
select @v = title_vector from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov'

select top (10) * from [$vector].find_similar$wikipedia_articles_embeddings$title_vector(@v, 50, 0.75) order by  cosine_similarity desc


--- CONTENT

declare @v nvarchar(max)
select @v = content_vector from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov'

select top (10) * from [$vector].find_similar$wikipedia_articles_embeddings$content_vector(@v, 1, 0.75) order by  cosine_similarity desc


declare @v nvarchar(max)
select @v = content_vector from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov'

select top (10) * from [$vector].find_similar$wikipedia_articles_embeddings$content_vector(@v, 50, 0.75) order by  cosine_similarity desc
