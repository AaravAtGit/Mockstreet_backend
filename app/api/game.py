from typing import List, Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.api.deps import get_current_user, get_current_active_verified_user
from app.db.session import get_db
from app.models.user import User
from app.models.room import Room
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.schemas.position import TradeRequest, PositionResponse
from app.schemas.portfolio import PortfolioResponse
from app.services.market_engine import market_service

router = APIRouter()



@router.get("/portfolio", response_model=PortfolioResponse)
def get_my_portfolio(
    room_id: int,
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
    db: Session = Depends(get_db),
):
    portfolio = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.room_id == room_id
    ).first()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found for this room")
        
    portfolio.username = current_user.username
    return portfolio

@router.post("/trade", response_model=PositionResponse)
def place_trade(
    room_id: int,
    trade_in: TradeRequest,
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
    db: Session = Depends(get_db),
):
    # 1. Get Portfolio
    portfolio = db.query(Portfolio).filter(
        Portfolio.user_id == current_user.id,
        Portfolio.room_id == room_id
    ).first()
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")

    # 2. Get Price from Market Service
    # We need the room symbol.
    room = db.query(Room).filter(Room.id == room_id).first()
    if not room:
         raise HTTPException(status_code=404, detail="Room not found")
         
    if room.status != "ACTIVE":
        raise HTTPException(status_code=400, detail="Game not active. Waiting for players.")
         
    current_price = market_service.get_current_price(room_id, room.symbol)
    
    if current_price <= 0:
        # Fallback or error if no price data available
        # checking if we can get a price, otherwise raise error
        # For robust game, maybe fallback to last known close from DB if live is 0? 
        # The service already does fallback. If still 0, then we have NO data.
        raise HTTPException(status_code=500, detail="Market data unavailable")

    # 3. Calculate Cost (Margin)
    # Cost = (Price * Qty) / Leverage
    cost = (current_price * trade_in.quantity) / trade_in.leverage
    
    if portfolio.current_balance < cost:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    # 4. Deduct Balance
    portfolio.current_balance -= cost
    
    # 5. Create Position
    position = Position(
        portfolio_id=portfolio.id,
        side=trade_in.side,
        quantity=trade_in.quantity,
        leverage=trade_in.leverage,
        entry_price=current_price,
        is_open=True
    )
    db.add(position)
    db.commit()
    db.refresh(position)
    
    return position

@router.post("/close/{position_id}", response_model=PositionResponse)
def close_trade(
    position_id: int,
    current_user: Annotated[User, Depends(get_current_active_verified_user)],
    db: Session = Depends(get_db),
):
    # 1. Get Position (ensure user owns it)
    position = db.query(Position).join(Portfolio).filter(
        Position.id == position_id,
        Portfolio.user_id == current_user.id
    ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
        
    if not position.is_open:
        raise HTTPException(status_code=400, detail="Position already closed")
    
    # Get Room to get Symbol
    room = position.portfolio.room
    
    # 2. Get Price
    exit_price = market_service.get_current_price(room.id, room.symbol)
    if exit_price <= 0:
         raise HTTPException(status_code=500, detail="Market data unavailable")
    
    # 3. Calculate PnL
    # PnL = (Exit - Entry) * Qty * Direction * Leverage
    direction = 1 if position.side == "LONG" else -1
    pnl = (exit_price - position.entry_price) * position.quantity * direction * position.leverage
    
    # 4. Return Margin + PnL to Balance
    # Exact margin used was (Entry * Qty) / Leverage
    margin_used = (position.entry_price * position.quantity) / position.leverage
    
    position.portfolio.current_balance += (margin_used + pnl)
    
    # 5. Update Position
    position.is_open = False
    position.exit_price = exit_price
    position.exit_time = func.now()
    position.pnl = pnl
    
    db.commit()
    db.refresh(position)
    
    return position
