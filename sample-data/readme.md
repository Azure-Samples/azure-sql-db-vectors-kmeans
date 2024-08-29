# Wikipedia Sample Dataset

## Download dataset

Download the wikipedia embeddings from here: https://cdn.openai.com/API/examples/data/vector_database_wikipedia_articles_embedded.zip and unzip it in the `/sample-data` folder.

In Windows with powershell:

```powershell
Invoke-WebRequest -Uri "https://cdn.openai.com/API/examples/data/vector_database_wikipedia_articles_embedded.zip" -OutFile "vector_database_wikipedia_articles_embedded.zip" 
```

or on Linux/MacOS with wget

```bash
wget https://cdn.openai.com/API/examples/data/vector_database_wikipedia_articles_embedded.zip
```

Then unzip its content in the src/sample-data folder.

In Windows with powershell:

```powershell
Expand-Archive .\vector_database_wikipedia_articles_embedded.zip .
```

or on Linux/MacOS with unzip:

```bash
unzip ./vector_database_wikipedia_articles_embedded.zip
```

## Import dataset into Azure SQL 

Upload the `vector_database_wikipedia_articles_embedded.csv` file (using [Azure Storage Explorer](https://learn.microsoft.com/azure/vs-azure-tools-storage-manage-with-storage-explorer?tabs=windows) for example) to an Azure Blob Storage container.

For this the example, the unzipped csv file `vector_database_wikipedia_articles_embedded.csv` is assumed to be uploaded to a blob container name `playground` and in a folder named `wikipedia`.

Once the file is uploaded, get the [SAS token](https://learn.microsoft.com/azure/storage/common/storage-sas-overview) to allow Azure SQL database to access it. (From Azure storage Explorer, right click on the `playground` container and than select `Get Shared Access Signature`. Set the expiration date to some time in future and then click on "Create". Copy the generated query string somewhere, for example into the Notepad, as it will be needed later)

Use a client tool like [Azure Data Studio](https://azure.microsoft.com/products/data-studio/) to connect to an Azure SQL database and then use the `01-import-data.sql` to create the `wikipedia_articles_embeddings` where the uploaded CSV file will be imported.

Make sure to replace the `<account>` and `<sas-token>` placeholders with the value correct for your environment:

- `<account>` is the name of the storage account where the CSV file has been uploaded
- `<sas-token>` is the Share Access Signature obtained before

Run each section (each section starts with a comment) separately. At the end of the process (will take up to a couple of minutes) you will have all the CSV data imported in the `wikipedia_articles_embeddings` table.

## Convert the existing vector embedding into a native binary format

The embeddings are available in a JSON array and they can be converted into the native binary format using the script `02-use-native-vectors.sql`