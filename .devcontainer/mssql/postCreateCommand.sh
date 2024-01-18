#!/bin/bash
sqlfiles="false"
SApassword=$1
sqlpath=$2

echo "SELECT * FROM SYS.DATABASES" | dd of=testsqlconnection.sql
for i in {1..60};
do
    /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P $SApassword -d master -i testsqlconnection.sql -C > /dev/null
    if [ $? -eq 0 ]
    then
        echo "SQL server ready"
        break
    else
        echo "Not ready yet..."
        sleep 1
    fi
done
rm testsqlconnection.sql

for f in $sqlpath/*
do
    if [ $f == $sqlpath/*".sql" ]
    then
        sqlfiles="true"
        echo "Found SQL file $f"
    fi
done

if [ $sqlfiles == "true" ]
then
    for f in $sqlpath/*
    do
        if [ $f == $sqlpath/*".sql" ]
        then
            echo "Executing $f"
            /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P $SApassword -d master -C -i $f
        fi
    done
fi