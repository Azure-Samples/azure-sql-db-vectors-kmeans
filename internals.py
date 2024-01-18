import logging

from pydantic import BaseModel
from vex.database import DatabaseEngine
from vex.index import NoIndex
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from config import INDEX

_logger = logging.getLogger("uvicorn")

class Vector(BaseModel):
    id: int = None
    vector: list[float] = []

class State:
    def __init__(self) -> None:
        self._scheduler = BackgroundScheduler()
        self.database_engine = DatabaseEngine(INDEX)
        self.index = NoIndex()
        pass

    def get_scheduler(self) -> BackgroundScheduler:
        return self._scheduler
    
    def clear(self):
        self._scheduler.shutdown()
        self._scheduler = None
        self.database_engine = None
        self.index = None

class CronParser:
    def __init__(self) -> None:
        self._configuration = INDEX

    def _get_cron_trigger(self, property_name, default_value) -> CronTrigger:
        cron_exp = self._configuration[property_name] or default_value
        cron_items = cron_exp.split(" ")
        if (len(cron_items) != 6):
            raise Exception("crontab expression must have 6 values (sec min hour day_of_month month day_of_week).")

        return CronTrigger(
            second=cron_items[0],
            minute=cron_items[1],
            hour=cron_items[2],
            day=cron_items[3],
            month=cron_items[4],
            day_of_week=cron_items[5]
        )
    
    def get_change_tracking_trigger(self) -> CronTrigger:
        t = self._get_cron_trigger("CHANGE_TRACKING_CRONTAB", "*/1 * * * * *")
        _logger.info("Change Tracking Trigger Schedule: " + str(t))
    
    def get_save_index_trigger(self) -> CronTrigger:
        t = self._get_cron_trigger("SAVE_INDEX_CRONTAB", "* */1 * * * *")
        _logger.info("Save Index Schedule: " + str(t))
    

   
    