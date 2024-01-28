import json
import os
import math
import pickle
import logging
import numpy as np
from .index import BaseIndex
from .database import DatabaseEngine, DatabaseEngineException
from .utils import DataSourceConfig
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
    def __init__(self) -> None:
        super().__init__()
        self.index = None
        self._db:DatabaseEngine = None
   
    def from_config(config:DataSourceConfig):
        index = KMeansIndex()
        index._db = DatabaseEngine.from_config(config)
        return index

    def from_id(id:int):
        index = KMeansIndex()
        index._db = DatabaseEngine.from_id(id)
        return index
    
    def initialize_build(self, force: bool)->int:
        id = None
        try:
            self._db.initialize();
            id = self._db.create_index_metadata(force)
            self.id = id
            _logger.info(f"Index has id {id}.")
        except DatabaseEngineException as e:
            raise Exception(f"Error initializing index: {str(e)}")
        return id

    def build(self):
        if (self.id == None):
            raise Exception("Index has not been initialized.")
        
        try:
            self.index = None
            
            _logger.info(f"Starting creating IVFFLAT index...")

            _logger.info("Loading data...")
            self._db.update_index_metadata("LOADING_DATA")
            ids, vectors = self._db.load_vectors_from_db()
            _logger.info("Done loading data...")
            
            _logger.info("Creating kmeans model...")
            self._db.update_index_metadata("KMEANS_CLUSTERING")
            nvp = np.asarray(vectors)
            vector_count:int = np.shape(nvp)[0]
            dimensions_count:int = np.shape(nvp)[1]
            if (vector_count > 1000000):
                clusters = int(math.sqrt(vector_count))
            else:
                clusters = int(vector_count / 1000)
            _logger.info(f"Determining {clusters} clusters...")        
            kmeans = MiniBatchKMeans(init="k-means++", n_clusters=clusters)             
            kmeans.fit(nvp)
            self.index = KMeansIndexIdMap(ids, kmeans, vector_count, dimensions_count)
            
            _logger.info(f"Done creating kmeans model ({type(kmeans)}).") 
            
            _logger.info(f"Saving centroids index #{self.id}...")
            self._db.update_index_metadata("SAVING_CENTROIDS")
            centroids = self.index.model.cluster_centers_
            nc = normalize(centroids)
            self._db.save_clusters_centroids(nc)        
            _logger.info(f"Done saving centroids index #{self.id}...")

            _logger.info(f"Saving centroids elements ({len(ids)}) index #{self.id}...")        
            self._db.update_index_metadata("SAVING_CENTROIDS_ELEMENTS")
            ids = self.index.ids
            labels = self.index.model.labels_
            self._db.save_clusters_items(ids, labels)
            _logger.info(f"Done saving centroids elements index #{self.id}...")

            _logger.info(f"Creating similarity function...")
            self._db.update_index_metadata("CREATING_SIMILARITY_FUNCTION")
            self._db.create_similarity_function()
            _logger.info(f"Done creating similarity function.")
            
            _logger.info(f"Finalizing index #{self.id} metadata...")
            self._db.finalize_index_metadata(self.index.vectors_count)
            _logger.info(f"Done finalizing metadata.")

            _logger.info(f"IVFFLAT Index #{self.id} created.")
        except Exception as e:  
            self._db.update_index_metadata("ERROR_DURING_CREATION")
            raise e    