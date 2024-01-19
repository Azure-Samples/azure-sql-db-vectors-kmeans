from db.index import NoIndex
from pydantic import BaseModel

class TableInfo(BaseModel):
    schema: str
    table: str

class ColumnInfo(BaseModel):
    id: str 
    vector: str

class VectorInfo(BaseModel):
    dimensions: int

class IndexRequest(BaseModel):
    table: TableInfo
    column: ColumnInfo
    vector: VectorInfo 

class State:
    def __init__(self) -> None:
        self.index = NoIndex()
        self.status = "idle"

    def set_status(self, status:str):   
        self.status = status

    def get_status(self)->str:
        return {
            "status": self.status,
            "index_id": self.index.id
        }  

    def clear(self):
        self.status = "idle"
        self.index = NoIndex()