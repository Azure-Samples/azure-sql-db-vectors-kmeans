/*
    Add columns to store the native vectors
*/
alter table wikipedia_articles_embeddings
add title_vector_ada2 vector(1536);

alter table wikipedia_articles_embeddings
add content_vector_ada2 vector(1536);
go
	
/*
    Update the native vectors
*/
update 
    wikipedia_articles_embeddings
set 
    title_vector_ada2 = cast(title_vector as vector(1536)),
    content_vector_ada2 = cast(content_vector as vector(1536))
go

/*
    Remove old columns
*/
alter table wikipedia_articles_embeddings
drop column title_vector;
go

alter table wikipedia_articles_embeddings
drop column content_vector;
go

/*
	Add primary key
*/
alter table [dbo].[wikipedia_articles_embeddings]
add constraint pk__wikipedia_articles_embeddings primary key clustered (id)
go

/*
	Add index on title
*/
create index [ix_title] on [dbo].[wikipedia_articles_embeddings](title)
go

/*
	Verify data
*/
select top (100) * from [dbo].[wikipedia_articles_embeddings]
go

select * from [dbo].[wikipedia_articles_embeddings] where title = 'Alan Turing'
go
