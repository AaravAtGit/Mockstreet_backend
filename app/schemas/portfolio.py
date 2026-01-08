from typing import List
from pydantic import BaseModel
from app.schemas.position import PositionResponse

class PortfolioBase(BaseModel):
    initial_balance: float = 100000.0

class PortfolioResponse(PortfolioBase):
    id: int
    username: str
    room_id: int
    current_balance: float
    positions: List[PositionResponse] = []

    class Config:
        from_attributes = True
