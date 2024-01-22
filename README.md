# Azure SQL DB Vector - KMeans Compute Node

Perform Approximate Nearest Neighbor (ANN) search on a vector column in Azure SQL DB using KMeans clustering.

As KMeans clustering is a compute intensive operation, this project uses SciKit Learn library to perform the clustering and stores the results in a SQL DB table. The results are then used to perform ANN search on the vector column.

To make the integration with SQL DB seamless, this project uses Azure Container Apps and expose the KMeans clustering as a REST API.

Vector data is stored in Azure SQL with no additional dependencies as shown in this repository: https://github.com/Azure-Samples/azure-sql-db-openai. The same dataset is used also in this project.

## Vector Search Optimization via Voronoi Cells and Inverted File Index

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

Scikit Learn is executed within a container as a REST endpoint. The API exposed by the container are:

- Server Status: `GET /`
- Build Index: `POST /kmeans/build`
- Rebuild Index: `POST /kmeans/rebuild`

Both Build and Rebuild API are asynchronous. The Server Status API can be used to check the status of the build process. 

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

```
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

## Download and import the Wikipedia Article with Vector Embeddings


## Run the project locally

The project take advantage of [Dev Container](https://code.visualstudio.com/docs/devcontainers/containers) to run the project locally. Make sure to have Docker Desktop installed and running on your machine.


- import wikipedia zip and save it in src/sample-data

- azd init

- azd env set MSSQL variable

- azd up

https://learn.microsoft.com/en-us/azure/developer/azure-developer-cli/manage-environment-variables


cd src
uvicorn main:api --reload


(short, 1-3 sentenced, description of the project)

## Deploy the project to Azure

