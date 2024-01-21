from db.index import NoIndex
from pydantic import BaseModel, Field

class TableInfo(BaseModel):
    table_schema: str = Field(alias="schema")
    table_name: str = Field(alias="name")

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
        self.current_status = "idle"
        self.last_status = "idle"

    def set_status(self, status:str):   
        self.last_status = self.current_status
        self.current_status = status

    def get_status(self)->str:
        return {
            "status": {
                "current": self.current_status,
                "last": self.last_status
            },
            "index_id": self.index.id
        }  

    def clear(self):
        self.last_status = self.current_status
        self.current_status = "idle"
        self.index = NoIndex()