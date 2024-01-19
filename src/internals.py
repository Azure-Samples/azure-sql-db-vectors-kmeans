from db.index import NoIndex
from pydantic import BaseModel

class TableInfo(BaseModel):
    schema: str = None
    table: str = None

class ColumnInfo(BaseModel):
    id: str = None
    vector: str = None

class VectorInfo(BaseModel):
    dimensions: int = None

class IndexRequest(BaseModel):
    table: TableInfo = None
    column: ColumnInfo = None
    vector: VectorInfo = None

class State:
    def __init__(self) -> None:
        self.index = NoIndex()
        self.status = "idle"

    def set_status(self, status:str):   
        self.status = status

    def get_status(self)->str:
        return self.status  

    def clear(self):
        self.index = NoIndex()