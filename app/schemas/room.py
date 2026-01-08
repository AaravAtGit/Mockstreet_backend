from typing import Optional
from datetime import datetime
from pydantic import BaseModel

class RoomBase(BaseModel):
    name: str
    symbol: str

class RoomCreate(RoomBase):
    duration_seconds: int = 1800  # Default 30 minutes (can be 60-3600)

class RoomResponse(RoomBase):
    id: int
    status: str
    player1_username: Optional[str] = None
    player2_username: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: int = 1800

    class Config:
        from_attributes = True

class RoomStatusUpdate(BaseModel):
    status: str
