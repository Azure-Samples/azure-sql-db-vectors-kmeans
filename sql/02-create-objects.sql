use vectordb
go

/*
    Create $vector schema and $vector.index table
*/
if schema_id('$vector') is null begin
    exec('create schema [$vector] authorization dbo')
end
if object_id('[$vector].[index]') is null begin
    create table [$vector].[index]
    (
        [id] int not null,
        [type] varchar(50) not null,
        [class] varchar(50) not null,
        [data] varbinary(max) not null,
        [item_count] int not null,
        [vector_dimensions] int not null,
        [data_version] int not null default 0,
        [saved_on] datetime2 not null,
        primary key ([id], [type])
    )
end          
