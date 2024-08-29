/*
** Make sure to run the script in the `vectordb` database **
*/

/*
    Sample queries
*/

-- Show the number of clusters generated for the wikipedia_articles_embeddings table
select count(distinct cluster_id) from [$vector].[wikipedia_articles_embeddings$title_vector_ada2$clusters_centroids]
go

-- TITLE SEARCH
set statistics time on

-- Reference query, without using the IVFFLAT index
declare @v varbinary(8000);
select @v = title_vector_ada2 from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov';
select top(10) id, title, [$distance] = vector_distance('cosine', @v, title_vector_ada2) from dbo.wikipedia_articles_embeddings order by [$distance]
go

-- Find the 10 most similar articles to 'Isaac Asimov' based on the title vector
-- searching only in the closest cluster
declare @v varbinary(8000);
select @v = title_vector_ada2 from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov';
select id, title, [$distance] from [$vector].find_similar$wikipedia_articles_embeddings$title_vector_ada2(@v, 10, 1, 0.75) order by [$distance]
go


-- Find the 10 most similar articles to 'Isaac Asimov' based on the title vector
-- searching in the 10th closest cluster, in order to improve the recall
declare @v varbinary(8000);
select @v = title_vector_ada2 from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov';
select id, title, [$distance] from [$vector].find_similar$wikipedia_articles_embeddings$title_vector_ada2(@v, 10, 10, 0.75) order by [$distance]
go

-- Find the 10 most similar articles to 'Isaac Asimov' based on the title vector
-- Searching in all clusters (50 clusters are generated for the wikipedia_articles_embeddings table)
-- This is equivalent to a full scan of the table, and it provides the best recall at the exposense of performances
declare @v varbinary(8000);
select @v = title_vector_ada2 from dbo.wikipedia_articles_embeddings where title = 'Isaac Asimov';
select top(10) id, title, [$distance] from [$vector].find_similar$wikipedia_articles_embeddings$title_vector_ada2(@v, 10, 50, 0.75) order by [$distance]
go
