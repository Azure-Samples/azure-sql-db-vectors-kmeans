import os
import logging

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, status as HTTPStatus, Response
from contextlib import asynccontextmanager
from pydantic import BaseModel
from apscheduler.schedulers.background import BackgroundScheduler

from db.index import NoIndex
from db.database import DatabaseEngine
from db.utils import IndexStatus, IndexSubStatus, UpdateResult
from db.kmeans import KMeansIndex
from internals import State, CronParser

load_dotenv()

api_version = "0.0.1"

_logger = logging.getLogger("uvicorn")

state = State()

@asynccontextmanager
async def lifespan(app: FastAPI):
    cp = CronParser()

    _logger.info("Activating Scheduler...")
    scheduler = state.get_scheduler()
    scheduler.add_job(change_tracking_monitor, cp.get_change_tracking_trigger(), id='change_monitor', coalesce=True)
    scheduler.add_job(save_index, cp.get_save_index_trigger(), id='save_index', coalesce=True)
    scheduler.add_job(bootstrap, id="bootstrap")
    scheduler.start()    

    _logger.info("Starting API...")
    yield
    _logger.info("Closing API...")
    state.clear()

api = FastAPI(lifespan=lifespan)

def assert_index_is_ready():    
    if (state.index.status != IndexStatus.TRAINED):
        raise HTTPException(
            status_code = HTTPStatus.HTTP_400_BAD_REQUEST, 
            detail = state.index.get_status()
        )

def bootstrap():
    _logger.info("Bootstrapping...")
    state.database_engine.initialize()
    _logger.info("Bootstrap complete.")

def save_index():
    if (state.index.status != IndexStatus.TRAINED):
        return
    
    if (state.index.substatus == IndexSubStatus.SAVING):
        return;
    
    s = state.get_scheduler()
    s.pause_job("save_index")

    state.index.save()

    s.resume_job("save_index")

def change_tracking_monitor():
    if (state.index.status != IndexStatus.TRAINED):
        return

    s = state.get_scheduler()
    s.pause_job("change_monitor")

    ur = state.index.update()

    match ur:
        case UpdateResult.NO_CHANGES:  
            s.resume_job("change_monitor")
        case UpdateResult.DONE:  
            s.resume_job("change_monitor")
        case UpdateResult.INDEX_IS_STALE:
            print(f"No changes found as index is stale. Full rebuild is needed.")
            print(f"Change detection is stopped.")
            s.remove_job("change_monitor")       
        case UpdateResult.UNKNOWN:
            print(f"No changes found. Reason unknown.")
            print(f"Change detection is stopped.")
            s.remove_job("change_monitor")       

@api.get("/")
def welcome():
    return {
            "server": "running",
            "version": api_version,
            "index": state.database_engine.get_info()
            }

@api.post("/kmeans/create")
def kmeans_create(tasks: BackgroundTasks): 
    if (isinstance(state.index, NoIndex)):
        _logger.info("No index found, creating KMEANS index...")
        state.index = KMeansIndex(state.database_engine)

    tasks.add_task(state.index.create)    
    return Response(status_code=202)

@api.post("/kmeans/load/{index_id}")
def faiss_create(tasks: BackgroundTasks, index_id: int):      
    if (isinstance(state.index, NoIndex)):
        _logger.info("No index found, loading KMEANS index...")
        state.index = KMeansIndex(state.database_engine)

    state.index._index_id = index_id
    tasks.add_task(state.index.load)    
    return Response(status_code=202)

@api.post("/kmeans/save")
def kmeans_save(tasks: BackgroundTasks):    
    assert_index_is_ready()
    tasks.add_task(state.index.save, force_save=True)    
    return Response(status_code=202)

@api.get("/kmeans/info")
def kmeans_info():
    return {
        "state": state.index.get_status()
    }