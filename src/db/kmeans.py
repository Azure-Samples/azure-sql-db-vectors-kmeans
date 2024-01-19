import json
import os
import math
import pickle
import logging
import numpy as np
from .index import BaseIndex
from .database import DatabaseEngine
from .utils import DataSourceConfig, NpEncoder, IndexStatus, IndexSubStatus
from sklearn.cluster import MiniBatchKMeans
from sklearn.preprocessing import normalize

_logger = logging.getLogger("uvicorn")

class KMeansIndexIdMap:
    ids: np.array
    model: MiniBatchKMeans

    def __init__(self, ids:np.array, model:MiniBatchKMeans, vector_count:int, dimensions_count:int) -> None:
        self.ids = ids
        self.model = model
        self.vectors_count:int = vector_count
        self.dimensions_count:int = dimensions_count

class KMeansIndex(BaseIndex):
    def __init__(self, config:DataSourceConfig) -> None:
        super().__init__()
        self.index = None
        self._db = DatabaseEngine(config=config)

    def initialize_build(self)->int:
        self._db.initialize();
        id = self._db.create_index_metadata()
        _logger.info(f"Index has been assigned id {id}.")
        return id

    def build(self):
        self.status = IndexStatus.CREATING
        self.index = None
        
        _logger.info(f"Starting created index...")

        _logger.info("Loading data...")
        ids, vectors = self._db.load_vectors_from_db()
        
        _logger.info("Creating kmeans model...")
        nvp = np.asarray(vectors)
        vector_count:int = np.shape(nvp)[0]
        dimensions_count:int = np.shape(nvp)[1]
        if (vector_count > 1000000):
            clusters = int(math.sqrt(vector_count))
        else:
            clusters = int(vector_count / 1000) * 2
        _logger.info(f"Determining {clusters} clusters...")        
        kmeans = MiniBatchKMeans(init="k-means++", n_clusters=clusters, n_init=10, random_state=0) 
        kmeans.fit(nvp)
        _logger.info(f"Done creating kmeans model ({type(kmeans)}).") 

        self.index = KMeansIndexIdMap(ids, kmeans, vector_count, dimensions_count)
        self.status = IndexStatus.TRAINED
        self.substatus = IndexSubStatus.READY
        
        _logger.info(f"Updating index metadata...")
        self.substatus = IndexSubStatus.SAVING
        self._db.update_index_metadata(self.index.vectors_count)
        _logger.info(f"Done updating metadata.")
        
        _logger.info(f"Saving centroids index #{id}...")
        centroids = self.index.model.cluster_centers_
        nc = normalize(centroids)
        self._db.save_clusters_centroids(nc)        
        _logger.info(f"Done saving centroids index #{id}...")

        _logger.info(f"Saving centroids elements ({len(ids)}) index #{id}...")        
        ids = self.index.ids
        labels = self.index.model.labels_
        self._db.save_clusters_items(ids, labels)
        _logger.info(f"Done saving centroids elements index #{id}...")

        #self._db.create_similarity_function()

    def get_status(self):
        if (self.index):
            return {
                "id": self._db._index_id,
                "type": type(self.index).__name__,
                "status": self.status,
                "substatus": self.substatus,
                "data_version": self._data_version,
                "saved_data_version": self._saved_data_version,
                "dimensions": self.index.dimensions_count,
                "vectors": self.index.vectors_count,
                "clusters": self.index.model.n_clusters
            }
        else:
            return {
                "status": self.status,
                "substatus": self.substatus,
                "data_version": self._data_version
            }