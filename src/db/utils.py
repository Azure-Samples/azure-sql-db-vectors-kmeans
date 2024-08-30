import json
import struct
import logging
import numpy as np
from enum import StrEnum, Enum

_logger = logging.getLogger("uvicorn")

def array_to_vector(a:list[float])->bytearray:
    # header
    b = bytearray([0xA9, 0x01])

    # number of items
    b += bytearray(struct.pack("i", len(a)))
    pf = f"{len(a)}f"

    # filler
    b += bytearray([0,0])

    # items
    b += bytearray(struct.pack(pf, *a))

    return b

def vector_to_array(b:bytearray)->list[float]:
    # header
    h = struct.unpack_from("2B", b, 0)    
    assert h == (169,1)

    c = int(struct.unpack_from("i", b, 2)[0])
    pf = f"{c}f"
    a = struct.unpack_from(pf, b, 8)
    return a

class DataSourceConfig:
    source_table_schema:str
    source_table_name:str
    source_id_column_name:str
    source_vector_column_name:str
    vector_dimensions:int
    
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
    
