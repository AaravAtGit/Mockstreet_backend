from datetime import datetime
from pydantic import BaseModel

class CandleBase(BaseModel):
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

class CandleCreate(CandleBase):
    pass

class Candle(CandleBase):
    id: int

    class Config:
        from_attributes = True
