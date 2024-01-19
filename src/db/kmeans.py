import json
import os
import math
import pickle
import logging
import numpy as np
from .index import BaseIndex
from .database import DatabaseEngine
from .utils import NpEncoder, IndexStatus, IndexSubStatus, UpdateResult
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
    def __init__(self, db:DatabaseEngine) -> None:
        super().__init__()
        self._data_version:int = 0
        self._saved_data_version:int = 0
        self.index = None
        self._db = db
        self._index_id:int = db._index_id

    def create(self):
        self.status = IndexStatus.CREATING
        self.index = None
        
        _logger.info(f"Starting created index #{self._index_id}...")

        _logger.info("Loading data...")
        version, ids, vectors = self._db.load_vectors_from_db()
        
        _logger.info("Creating index...")
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
        _logger.info(f"Done creating index ({type(kmeans)}).") 

        self.index = KMeansIndexIdMap(ids, kmeans, vector_count, dimensions_count)
        self._data_version = version
        self._saved_data_version = None
        self.status = IndexStatus.TRAINED
        self.substatus = IndexSubStatus.READY

    def load(self):
        self.status = IndexStatus.LOADING
        self.substatus: IndexSubStatus.NONE
        self.index = None
        
        _logger.info(f"Loading index #{self._index_id}...")
        
        pkl, version = self._db.load_index()   
        
        if pkl == None:
            _logger.info("No index found.")
        else:
            self.index = pickle.loads(pkl)
            _logger.info(f"Done loading index #{self._index_id}.")

        if (self.index):
            self._data_version = version
            self._saved_data_version = version
            self.status = IndexStatus.TRAINED
            self.substatus = IndexSubStatus.READY
        else:
            self._data_version = 0
            self._saved_data_version = 0
            self.status = IndexStatus.NOINDEX
            self.substatus = IndexSubStatus.NONE

    def save(self, force_save=False):
        if not (self.status == IndexStatus.TRAINED and 
            self.substatus == IndexSubStatus.READY):
            return
        
        if (self._data_version == self._saved_data_version and not force_save):
            return
        
        _logger.info(f"Saving index #{self._index_id}...")
        self.substatus = IndexSubStatus.SAVING
        pkl = pickle.dumps(self.index)
        self._db.save_index(
            "kmeans", 
            type(self.index).__name__,
            pkl, 
            self.index.vectors_count, 
            self.index.dimensions_count, 
            self._data_version)
        self._saved_data_version = self._data_version        
        _logger.info(f"Done saving index #{self._index_id}.")
        self.save_clusters_centroids()
        self.save_clusters_items()
        self._db.create_similarity_function()

    def save_clusters_centroids(self):
        _logger.info(f"Saving centroids index #{self._index_id}...")
        centroids = self.index.model.cluster_centers_
        nc = normalize(centroids)
        self._db.save_clusters_centroids(nc)        
        _logger.info(f"Done saving centroids index #{self._index_id}...")

    def save_clusters_items(self):
        ids = self.index.ids
        labels = self.index.model.labels_
        _logger.info(f"Saving centroids elements ({len(ids)}) index #{self._index_id}...")        
        self._db.save_clusters_items(ids, labels)
        _logger.info(f"Done saving centroids elements index #{self._index_id}...")
       
    def get_status(self):
        if (self.index):
            return {
                "id": self._index_id,
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
                "id": self._index_id,
                "status": self.status,
                "substatus": self.substatus,
                "data_version": self._data_version
            }