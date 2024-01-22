/*
    Sample queries
*/

-- Show the number of clusters generated for the wikipedia_articles_embeddings table
select count(distinct cluster_id) from [$vector].[wikipedia_articles_embeddings$content_vector$clusters_centroids]
go

-- TITLE SEARCH

-- Store the vector represeting 'Isaac Asimov' in a variable
declare @v nvarchar(max);
select @v = title_vector from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov';

-- Find the 10 most similar articles to 'Isaac Asimov' based on the title vector
-- searching only in the closest cluster
select top (10) * from [$vector].find_similar$wikipedia_articles_embeddings$title_vector(@v, 1, 0.75) order by  cosine_similarity desc

-- Find the 10 most similar articles to 'Isaac Asimov' based on the title vector
-- searching in the 10th closest cluster, in order to improve the recall
select top (10) * from [$vector].find_similar$wikipedia_articles_embeddings$title_vector(@v, 10, 0.75) order by  cosine_similarity desc

-- Find the 10 most similar articles to 'Isaac Asimov' based on the title vector
-- Searching in all clusters (50 clusters are generated for the wikipedia_articles_embeddings table)
-- This is equivalent to a full scan of the table, and it provides the best recall
select top (10) * from [$vector].find_similar$wikipedia_articles_embeddings$title_vector(@v, 50, 0.75) order by  cosine_similarity desc
go

--- CONTENT SEARCH

--- Same as for TITLE sample, but on CONTENT

declare @v nvarchar(max)
select @v = content_vector from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov'
select top (10) * from [$vector].find_similar$wikipedia_articles_embeddings$content_vector(@v, 1, 0.75) order by  cosine_similarity desc
go

declare @v nvarchar(max)
select @v = content_vector from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov'
select top (10) * from [$vector].find_similar$wikipedia_articles_embeddings$content_vector(@v, 50, 0.75) order by  cosine_similarity desc
go