from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class PositionBase(BaseModel):
    side: str
    quantity: float
    leverage: int = 1

class TradeRequest(PositionBase):
    # Symbol is inferred from the Room
    pass

class PositionResponse(PositionBase):
    id: int
    portfolio_id: int
    entry_price: float
    entry_time: datetime
    exit_price: Optional[float] = None
    exit_time: Optional[datetime] = None
    is_open: bool
    pnl: Optional[float] = None

    class Config:
        from_attributes = True
