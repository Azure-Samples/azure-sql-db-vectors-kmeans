/*
** Make sure to run the script in the `vectordb` database **
*/

/*
	Import data
*/
bulk insert dbo.[wikipedia_articles_embeddings]
from '/src/sample-data/vector_database_wikipedia_articles_embedded.csv'
with (
    format = 'csv',
    firstrow = 2,
	fieldterminator = ',',
	rowterminator = '0x0a',
    fieldquote = '"',
    batchsize = 1000,
    tablock
)
go