# Azure SQL DB Vector - KMeans Compute Node

Perform Approximate Nearest Neighbor (ANN) search on a vector column in Azure SQL DB using KMeans clustering.

As KMeans clustering is a compute intensive operation, this project uses SciKit Learn library to perform the clustering and stores the results in a SQL DB table. The results are then used to perform ANN search on the vector column.

To make the integration with SQL DB seamless, this project uses Azure Container Apps and expose the KMeans clustering as a REST API.

Vector data is stored in Azure SQL with no additional dependencies as shown in this repository: https://github.com/Azure-Samples/azure-sql-db-openai. The same dataset is used also in this project.

## Table of Contents

- [Vector Search Optimization](#vector-search-optimization-via-voronoi-cells-and-inverted-file-index-aka-cell-probing)
- [Architecture](#architecture)
- [Run the project locally](#run-the-project-locally)
  - [Create the MSSQL DB](#create-the-mssql-db)
  - [Import sample dataset](#import-sample-dataset)
- [Deploy the project to Azure](#deploy-the-project-to-azure)
- [REST API](#rest-api)
  - [Build Index](#build-index)
  - [Rebuild Index](#rebuild-index)
  - [Query API Status](#query-api-status)
- [Search for similar articles](#search-for-similar-articles)

## Vector Search Optimization via Voronoi Cells and Inverted File Index (aka "Cell-Probing")

Given a vector, finding the most similar vector among all those stored in a database is a common problem in many applications. The easiest approach to solve this problem is to use a brute force approach, which is to compute the distance between the query vector and all the vectors stored in the database. This is a good approach when the number of vectors is not extremely big, and dimensionality of vectors is not very high, as it guarantees *perfect [recall](https://en.wikipedia.org/wiki/Precision_and_recall)*, meaning that all relevat items that should be returned are actually returned.

Unfortunately this approach is not scalable as the number of vectors stored in the database increases, so you may want to exchange a perfect recall for much better performances. This is where *approximate nearest neighbor* (ANN) search comes into play. ANN search algorithms are able to return the most similar vectors to the query vector, but they do not guarantee perfect recall. In other words, they may return less vectors than all the relevant to the query vector, but they are much faster than the brute force approach.

To speed up the search, it is possible to split the vectors into groups, making sure the create groups so that all vectors that are someone similar to each other are put in the same group. This is the idea behind *Voronoi cells*. 

TODO: VORONOI CELLS IMAGE

The idea is to create a set of *centroids* (i.e. vectors) and then assign each vector to the closest centroid. This way, all vectors that are similar to each other will be assigned to the same centroid. This is a very fast operation, as it is just a matter of computing the distance between the vector and all the centroids and then assign the vector to the closest centroid. Once all vectors are assigned to a centroid, it is possible to create a *inverted file index* that maps each centroid to the list of vectors assigned to it. This way, when a query vector is given, it is possible to find the closest centroid and then return all the vectors assigned to it. This is much faster than computing the distance between the query vector and all the vectors stored in the database.

This project uses KMeans clustering to create the centroids and then create the inverted file index. KMeans clustering is a very popular clustering algorithm that is able to create a given number of clusters (i.e. centroids) by iteratively moving the centroids to the center of the vectors assigned to them. The number of clusters is a parameter that can be tuned to trade off recall and performances. The more clusters are created, the better the recall, but the slower the search. The less clusters are created, the worse the recall, but the faster the search.

In this repo the number of cluster is determined by the following code:

```python
if (vector_count > 1000000):
    clusters = int(math.sqrt(vector_count))
else:
    clusters = int(vector_count / 1000) * 2 
```

## Architecture

## Run the project locally

The project take advantage of [Dev Container](https://code.visualstudio.com/docs/devcontainers/containers) to run the project locally. Make sure to have Docker Desktop installed and running on your machine.

Clone the repository and open it in VS Code. You'll be prompted to reopen the project in a Dev Container. Click on the "Reopen in Container" button.

Once the Dev Container is ready, open a terminal and run the following commands:

```bash
cd src
uvicorn main:api --reload
```

and you'll be good to go. The API will be available at http://127.0.0.1:8000.

### Create the MSSQL DB

The Dev Container sets up the container needed to run Scikit Learn and also the MSSQL DB needed to store the vectors and the clusters. A database named `vectordb` is created automatically along with the `dbo.wikipedia_articles_embeddings` table. 

You can use [Azure Data Studio](https://learn.microsoft.com/en-us/azure-data-studio/download-azure-data-studio) to connect to the MSSQL DB and run queries against it.

### Import sample dataset

Follow the instructions in the '/sample-data' folder to download the sample dataset. Once the `vector_database_wikipedia_articles_embedded.csv` is available you can import it into the MSSQL database using the script 

- `src/sql/00-import-data.sql`

You can now run the KMeans clustering algorithm using the following command as described in the [REST API](#REST%20API) section:

## Deploy the project to Azure

- azd init

- azd env set MSSQL variable

- azd up

https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/manage-environment-variables


## REST API

KMeans model from Scikit Learn is executed within a container as a REST endpoint. The API exposed by the container are:

- Server Status: `GET /`
- Build Index: `POST /kmeans/build`
- Rebuild Index: `POST /kmeans/rebuild`

Both Build and Rebuild API are asynchronous. The Server Status API can be used to check the status of the build process. 

### Build Index

To build an index from scratch, the Build API expects the following payload:

```
{
  "table": {
    "schema": <schema name>,
    "name": <table name>
  },
  "column": {
    "id": <id column name>,
    "vector": <vector column name>
  },
  "vector": {
    "dimensions": <dimensions>
  }
}
```

Using the aformentioned wikipedia dataset, the payload would be:

```http
POST /kmeans/build
{
  "table": {
    "schema": "dbo",
    "name": "wikipedia_articles_embeddings"
  },
  "column": {
    "id": "id",
    "vector": "content_vector"
  },
  "vector": {
    "dimensions": 1536
  }
}
```

The API would verify that the request is correct and then start the build process asynchrously returning the id assigned to the index being created:

```
```

And index on the same table and vector column already exists, the API would return an error. If you want to force the creation of a new index over the existing one you can use the `force` option:

```http
POST /kmeans/build?force=true
```

### Rebuild Index

If you need to rebuild an existing index, you can use the Rebuild API. The API doesn't need a payload as it will use the existing index definition. Just like the build process, also the rebuild process is asychronous. The index to be rebuilt is specifed via URL path:

```
POST /kmeans/rebuild/<index id>
```

for example, to rebuild the index with id 1:

```http
POST /kmeans/rebuild/1`
```

### Query API Status

The status of the build process can be checked using the Server Status API:

```http
GET /
```

and you'll get the current status and the last status reported. The checking the last status is useful to understand if an error occurred during the build process.

## Search for similar articles

TDB
