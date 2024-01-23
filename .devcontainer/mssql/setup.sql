use [tempdb]
go

/*
	create database
*/
if (db_id('vectordb') is null) begin
    exec('create database vectordb;')
end
go

use vectordb;
go

/*
    create login
*/
if not exists(select * from sys.server_principals where [name] = 'vectordb_user') begin
    create login [vectordb_user] with password = 'rANd0m_PAzzw0rd!';
end
go

/*
	create user
*/
if (user_id('vectordb_user') is null) begin
    create user [vectordb_user] from login vectordb_user;
    alter role db_owner add member vectordb_user;
end
go

/*
	create table
*/
if (object_id('[dbo].[wikipedia_articles_embeddings]') is null) begin
    create table [dbo].[wikipedia_articles_embeddings]
    (
        [id] [int] not null primary key,
        [url] [varchar](1000) not null,
        [title] [varchar](1000) not null,
        [text] [varchar](max) not null,
        [title_vector] [varchar](max) not null,
        [content_vector] [varchar](max) not null,
        [vector_id] [int] not null
    )
end
go
