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

    