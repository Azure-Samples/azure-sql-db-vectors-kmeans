import json
import numpy as np
from enum import StrEnum, Enum

class IndexStatus(StrEnum):
    INITIALIZING = 'initializing'
    NOT_READY = 'not ready'
    LOADING = 'loading'
    TRAINED = 'trained'
    READY = 'ready'
    CREATING = 'creating'
    TRAINING = 'training'    
    NOINDEX = 'noindex'

class IndexSubStatus(StrEnum):
    NONE = 'none'
    READY = 'ready'
    SAVING = 'saving'

class UpdateResult(Enum):
    DONE = 0
    NO_CHANGES = 1
    INDEX_NOT_READY = 2
    INDEX_IS_STALE = 3
    UNKNOWN = -1

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.int32):
            return int(obj)
        if isinstance(obj, np.int64):
            return int(obj)
        if isinstance(obj, np.integer):
            return int(obj)
        if isinstance(obj, np.floating):
            return float(obj)
        if isinstance(obj, np.float32):
            return float(obj)
        if isinstance(obj, np.ndarray):
            return obj.tolist()
        return super(NpEncoder, self).default(obj)

class Buffer:
    def __init__(self):
        self.ids = []
        self.vectors = []
             
    def add(self, id, vector):
        self.ids.append(id)
        self.vectors.append(vector)

    def clear(self):
        self.ids.clear()
        self.vectors.clear()

class VectorSet:
    def __init__(self, vector_dimensions:int):
        self.ids = np.empty((0), dtype=np.int32)
        self.vectors = np.empty((0, vector_dimensions), dtype=np.float32)      
             
    def add(self, buffer:Buffer):
        self.ids = np.append(self.ids, np.asarray(buffer.ids), 0)
        self.vectors = np.append(self.vectors, np.asarray(buffer.vectors, dtype=np.float32), 0)          

    def get_memory_usage(self):
        return self.ids.nbytes + self.vectors.nbytes
    
