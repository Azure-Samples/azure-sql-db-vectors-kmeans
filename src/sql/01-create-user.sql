use vectordb
go

/*
Create user to be used by python script
*/
create login vectordb_user with password='kOZ0I9DZ_mu4JXyETWH@2VQ8ovNQYOcmriJYEh9o=';
go
create user vectordb_user from login vectordb_user
go
alter role db_owner add member vectordb_user
go