import os
import logging
import json

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, Response, HTTPException

from db.index import NoIndex
from db.kmeans import KMeansIndex
from db.utils import DataSourceConfig
from internals import IndexRequest

load_dotenv()

api_version = "0.0.1"

_logger = logging.getLogger("uvicorn")

api = FastAPI()

_index = NoIndex()

@api.get("/")
def welcome():
    return {
        "server": "running",
        "version": api_version
    }

@api.post("/kmeans/build")
def build(tasks: BackgroundTasks, indexRequest: IndexRequest): 
    
    # TODO make sure not already building
    # TODO make sure index doesnt exits already    
    config = DataSourceConfig()
    config.source_table_schema = indexRequest.table.schema
    config.source_table_name = indexRequest.table.table
    config.source_id_column_name = indexRequest.column.id
    config.source_vector_column_name = indexRequest.column.vector 
    config.vector_dimensions = indexRequest.vector.dimensions
    _index = KMeansIndex(config)

    id = None
    try:
        id = _index.initialize_build()
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=500)

    tasks.add_task(_index.build) 

    r = {
            "id": int(id),
            "status": "building"
        }
    j = json.dumps(r, default=str)

    return Response(content=j, status_code=202, media_type='application/json')


@api.post("/kmeans/rebuild/{index_id}")
def rebuild(tasks: BackgroundTasks, index_id: int): 
    # TODO check if index exists
    pass


@api.get("/kmeans/info")
def kmeans_info():
    return {
        "state": ""
    }