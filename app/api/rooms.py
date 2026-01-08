from typing import List, Annotated
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.models.room import Room
from app.models.portfolio import Portfolio
from app.schemas.room import RoomCreate, RoomResponse

router = APIRouter()



@router.post("/", response_model=RoomResponse)
def create_room(
    room_in: RoomCreate,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db)
):
    # Validate duration (1 min to 60 min)
    duration = max(60, min(3600, room_in.duration_seconds))
    
    # 1. Create Room
    room = Room(
        name=room_in.name, 
        symbol=room_in.symbol, 
        player1_id=current_user.id,
        status="WAITING",
        duration_seconds=duration
    )
    db.add(room)
    db.commit()
    db.refresh(room)

    # 2. Create Portfolio for Player 1
    portfolio = Portfolio(
        user_id=current_user.id,
        room_id=room.id
    )
    db.add(portfolio)
    db.commit()
    
    # Manually populate usernames for response
    room.player1_username = current_user.username
    room.player2_username = None
    
    return room

@router.get("/", response_model=List[RoomResponse])
def list_rooms(
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db)
):
    rooms = db.query(Room).options(
        joinedload(Room.player1),
        joinedload(Room.player2)
    ).offset(skip).limit(limit).all()
    
    for room in rooms:
        room.player1_username = room.player1.username if room.player1 else None
        room.player2_username = room.player2.username if room.player2 else None
        
    return rooms

@router.post("/{room_id}/join", response_model=RoomResponse)
def join_room(
    room_id: int,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Session = Depends(get_db),
):
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
        
    if room.status != "WAITING":
        raise HTTPException(status_code=400, detail="Room is not accepting new players")

    if room.player1_id == current_user.id:
        raise HTTPException(status_code=400, detail="You are already in this room")

    # 1. Update Room
    room.player2_id = current_user.id
    room.status = "ACTIVE"
    room.started_at = datetime.now(timezone.utc)  # Mark game start time
    
    # 2. Create Portfolio for Player 2
    portfolio = Portfolio(
        user_id=current_user.id,
        room_id=room.id
    )
    db.add(portfolio)
    db.commit()
    db.refresh(room)
    
    # Populate usernames
    room.player1_username = room.player1.username if room.player1 else None # Should be loaded or available
    room.player2_username = current_user.username
    
    return room
