import asyncio
import json
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
from sqlalchemy.orm import Session, joinedload
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.models.room import Room
from app.models.portfolio import Portfolio
from app.models.candle import Candle
from app.services.market_engine import market_service

router = APIRouter()


def validate_ws_token(token: str, db: Session) -> Optional[User]:
    """Validate JWT token and return user."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        user = db.query(User).filter(User.email == email).first()
        return user
    except JWTError:
        return None


class PortfolioConnection:
    """Manages a single user's portfolio WebSocket connection."""
    
    def __init__(self, websocket: WebSocket, user_id: int, room_id: int):
        self.websocket = websocket
        self.user_id = user_id
        self.room_id = room_id
        self.is_active = True


class PortfolioManager:
    """Manages all portfolio WebSocket connections."""
    
    def __init__(self):
        self.connections: Dict[int, List[PortfolioConnection]] = {}  # room_id -> connections
    
    def add_connection(self, room_id: int, conn: PortfolioConnection):
        if room_id not in self.connections:
            self.connections[room_id] = []
        self.connections[room_id].append(conn)
    
    def remove_connection(self, room_id: int, conn: PortfolioConnection):
        if room_id in self.connections:
            self.connections[room_id] = [c for c in self.connections[room_id] if c != conn]


portfolio_manager = PortfolioManager()


def _calculate_position_pnl(position, current_price: float) -> dict:
    """Calculate PnL for a single position."""
    direction = 1 if position.side == "LONG" else -1
    unrealized_pnl = (current_price - position.entry_price) * position.quantity * direction * position.leverage
    
    return {
        "id": position.id,
        "side": position.side,
        "quantity": position.quantity,
        "leverage": position.leverage,
        "entry_price": position.entry_price,
        "current_price": current_price,
        "unrealized_pnl": round(unrealized_pnl, 2),
        "entry_time": position.entry_time.isoformat() if position.entry_time else None
    }


async def stream_portfolio(conn: PortfolioConnection):
    """Stream portfolio updates to a connected user."""
    db = SessionLocal()
    try:
        while conn.is_active:
            # Fetch user's portfolio with positions and room info
            portfolio = db.query(Portfolio).options(
                joinedload(Portfolio.positions),
                joinedload(Portfolio.room)
            ).filter(
                Portfolio.user_id == conn.user_id,
                Portfolio.room_id == conn.room_id
            ).first()
            
            if not portfolio:
                await conn.websocket.send_json({
                    "type": "error",
                    "message": "Portfolio not found"
                })
                break
            
            # Get current price from market service (cached)
            # Use room symbol from portfolio
            if portfolio.room:
                 current_price = market_service.get_current_price(conn.room_id, portfolio.room.symbol)
            else:
                 current_price = 0.0
            
            # Calculate positions with PnL
            open_positions = [p for p in portfolio.positions if p.is_open]
            positions_data = [_calculate_position_pnl(p, current_price) for p in open_positions]
            
            total_unrealized_pnl = sum(p["unrealized_pnl"] for p in positions_data)
            total_equity = portfolio.current_balance + total_unrealized_pnl
            
            # Send update
            await conn.websocket.send_json({
                "type": "portfolio_update",
                "balance": round(portfolio.current_balance, 2),
                "unrealized_pnl": round(total_unrealized_pnl, 2),
                "total_equity": round(total_equity, 2),
                "positions": positions_data,
                "current_price": current_price
            })
            
            # Refresh DB session for next iteration
            db.expire_all()
            await asyncio.sleep(1)
            
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Portfolio stream error: {e}")
    finally:
        conn.is_active = False
        db.close()


@router.websocket("/ws/portfolio/{room_id}")
async def portfolio_websocket(websocket: WebSocket, room_id: int):
    """
    Private portfolio WebSocket endpoint.
    
    Authentication: Send first message with {"type": "auth", "token": "jwt_token"}
    
    Streams user's positions with real-time PnL every second:
    {
        "type": "portfolio_update",
        "balance": 99500.0,
        "unrealized_pnl": 325.50,
        "total_equity": 99825.50,
        "positions": [
            {
                "id": 101,
                "side": "LONG",
                "quantity": 1.0,
                "leverage": 10,
                "entry_price": 150.00,
                "current_price": 150.35,
                "unrealized_pnl": 35.0
            }
        ]
    }
    """
    await websocket.accept()
    
    try:
        # Wait for authentication message
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
        
        if auth_data.get("type") != "auth" or "token" not in auth_data:
            await websocket.send_json({
                "type": "error",
                "message": "Expected auth message: {type: 'auth', token: 'jwt_token'}"
            })
            await websocket.close(code=4001)
            return
        
        # Validate token
        db = SessionLocal()
        try:
            user = validate_ws_token(auth_data["token"], db)
            if not user:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid or expired token"
                })
                await websocket.close(code=4003)
                return
            
            # Check user is in this room
            portfolio = db.query(Portfolio).filter(
                Portfolio.user_id == user.id,
                Portfolio.room_id == room_id
            ).first()
            
            if not portfolio:
                await websocket.send_json({
                    "type": "error",
                    "message": "You are not in this room"
                })
                await websocket.close(code=4004)
                return
            
            user_id = user.id
            username = user.username
        finally:
            db.close()
        
        # Authentication successful
        await websocket.send_json({
            "type": "auth_success",
            "username": username,
            "room_id": room_id
        })
        
        # Create connection and start streaming
        conn = PortfolioConnection(websocket, user_id, room_id)
        portfolio_manager.add_connection(room_id, conn)
        
        try:
            await stream_portfolio(conn)
        finally:
            portfolio_manager.remove_connection(room_id, conn)
            
    except asyncio.TimeoutError:
        await websocket.send_json({
            "type": "error",
            "message": "Authentication timeout"
        })
        await websocket.close(code=4002)
    except WebSocketDisconnect:
        pass
