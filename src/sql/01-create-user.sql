/*
** Make sure to run the script in the `vectordb` database **
*/

/*
Create user to be used by python script
*/
if (serverproperty('Edition') = 'SQL Azure') begin

    if not exists (select * from sys.database_principals where [type] in ('E', 'S') and [name] = 'vectordb_user')
    begin 
        create user [vectordb_user] with password = 'rANd0m_PAzzw0rd!'        
    end

    alter role db_owner add member [vectordb_user]
    
end else begin

    if not exists (select * from sys.server_principals where [type] in ('E', 'S') and [name] = 'vectordb_user')
    begin 
        create login [vectordb_user] with password = 'rANd0m_PAzzw0rd!'
    end    

    if not exists (select * from sys.database_principals where [type] in ('E', 'S') and [name] = 'vectordb_user')
    begin
        create user [vectordb_user] from login [vectordb_user]            
    end

    alter role db_owner add member [vectordb_user]
end

