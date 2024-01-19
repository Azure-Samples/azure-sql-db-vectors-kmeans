class BaseIndex:
    def __init__(self) -> None:
        self.id:int = None
 
    def build(self):
        pass

class NoIndex(BaseIndex):
    def __init__(self) -> None:
        super().__init__()
    