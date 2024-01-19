from .utils import IndexStatus, IndexSubStatus

class BaseIndex:
    def __init__(self) -> None:
        self.status:IndexStatus = IndexStatus.NOT_READY
        self.substatus:IndexSubStatus = IndexSubStatus.NONE
        self._index_num:int = None
 
    def create(self):
        pass

    def update(self):
        pass

    def load(self): 
        pass

    def get_status(self):
        return {
            "id": self._index_num,
            "status": self.status,
            "substatus": self.substatus            
        }
        
class NoIndex(BaseIndex):
    def __init__(self) -> None:
        super().__init__()
    