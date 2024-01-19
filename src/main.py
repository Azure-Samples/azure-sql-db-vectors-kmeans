import os
import logging
import json

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Response, HTTPException
from contextlib import asynccontextmanager

from db.index import NoIndex
from db.kmeans import KMeansIndex
from db.utils import DataSourceConfig
from internals import IndexRequest, State

load_dotenv()

api_version = "0.0.1"

_logger = logging.getLogger("uvicorn")

state = State()

@asynccontextmanager
async def lifespan(app: FastAPI):    
    _logger.info("Starting API...")
    yield
    _logger.info("Closing API...")
    state.clear()

api = FastAPI(lifespan=lifespan)

@api.get("/")
def welcome():
    return {
        "server":  state.get_status(),
        "version": api_version
    }

@api.post("/kmeans/build")
def build(tasks: BackgroundTasks, indexRequest: IndexRequest, force: bool = False): 
    if (isinstance(state.index, NoIndex) == False):        
        raise HTTPException(detail=f"An index (#{state.index.id}) is already being built.", status_code=500)
      
    config = DataSourceConfig()
    config.source_table_schema = indexRequest.table.schema
    config.source_table_name = indexRequest.table.table
    config.source_id_column_name = indexRequest.column.id
    config.source_vector_column_name = indexRequest.column.vector 
    config.vector_dimensions = indexRequest.vector.dimensions
    state.index = KMeansIndex.from_config(config)

    id = None
    try:
        state.set_status("initializing")
        id = state.index.initialize_build(force)
    except Exception as e:
        state.clear()
        raise HTTPException(detail=str(e), status_code=500)

    tasks.add_task(_internal_build) 

    r = {
            "id": int(id),
            "status": state.get_status()
        }
    j = json.dumps(r, default=str)

    return Response(content=j, status_code=202, media_type='application/json')

@api.post("/kmeans/rebuild/{index_id}")
def rebuild(tasks: BackgroundTasks, index_id: int): 
    if (isinstance(state.index, NoIndex) == False):        
        raise HTTPException(detail=f"An index (#{state.index.id}) is already being built.", status_code=500)

    try:
        state.index = KMeansIndex.from_id(index_id) 
        state.set_status("initializing")
        id = state.index.initialize_build(force=True)
    except Exception as e:
        state.clear()
        raise HTTPException(detail=str(e), status_code=500)

    tasks.add_task(_internal_build) 

    r = {
            "id": int(id),
            "status": state.get_status()
        }
    j = json.dumps(r, default=str)

    return Response(content=j, status_code=202, media_type='application/json')

def _internal_build():
    try:
        state.set_status("building")
        state.index.build()
    except Exception as e:
        _logger.error(f"Error building index: {e}")
    finally:
        state.clear()