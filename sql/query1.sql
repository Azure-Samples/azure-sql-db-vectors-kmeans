set statistics time on

declare @v nvarchar(max)
select @v = content_vector from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov'

select top (10) * from [$vector].find_similar$wikipedia_articles_embeddings(@v, 1, 0.75) order by  cosine_similarity desc


declare @v nvarchar(max)
select @v = content_vector from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov'

select top (10) * from [$vector].find_similar$wikipedia_articles_embeddings(@v, 50, 0.75) order by  cosine_similarity desc
