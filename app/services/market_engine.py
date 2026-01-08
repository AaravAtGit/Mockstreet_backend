import asyncio
import json
from typing import List, Dict, Optional
from fastapi import WebSocket
from sqlalchemy.orm import Session, joinedload
from app.db.session import SessionLocal
from app.models.candle import Candle
from app.models.room import Room
from app.models.portfolio import Portfolio
from app.models.position import Position
from sqlalchemy import func
from datetime import timedelta
import random

# Constants
DEFAULT_GAME_DURATION = 1800  # 30 minutes default (used if room has no duration set)
PRELOAD_CANDLES = 50  # Send 50 historical candles before starting


class GameRoom:
    """
    Manages a single game room's WebSocket connections and data streaming.
    Integrated with the database Room model for proper game state.
    """
    
    def __init__(self, room_id: int):
        self.room_id = room_id
        self.active_connections: List[WebSocket] = []
        self.history: List[dict] = []
        self.is_running = False
        self.task = None
        self.last_price: Optional[float] = None
        self.current_candle_index: int = 0
        
        # Cached room data (refreshed from DB)
        self.symbol: Optional[str] = None
        self.status: Optional[str] = None
        self.started_at: Optional[int] = None
        self.game_duration: int = DEFAULT_GAME_DURATION  # Will be set from room

    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection and start game loop if needed."""
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send existing history to new connection
        for data in self.history:
            await websocket.send_text(json.dumps(data))

        # Start game loop if not already running
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self.run_game_loop())

    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """Send a message to all connected clients."""
        self.history.append(message)
        
        # Update last price cache
        if "candle" in message and message["candle"]:
            self.last_price = float(message["candle"]["close"])
            
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                dead_connections.append(connection)
        
        for dead in dead_connections:
            self.disconnect(dead)

    def _get_room_from_db(self, db: Session) -> Optional[Room]:
        """Fetch room with portfolios and positions from database."""
        return db.query(Room).options(
            joinedload(Room.portfolios).joinedload(Portfolio.positions),
            joinedload(Room.portfolios).joinedload(Portfolio.user)
        ).filter(Room.id == self.room_id).first()

    def _calculate_player_stats(self, portfolio: Portfolio, current_price: float) -> dict:
        """Calculate unrealized PnL and stats for a player."""
        open_positions = [p for p in portfolio.positions if p.is_open]
        
        unrealized_pnl = 0.0
        for pos in open_positions:
            direction = 1 if pos.side == "LONG" else -1
            pnl = (current_price - pos.entry_price) * pos.quantity * direction * pos.leverage
            unrealized_pnl += pnl
        
        total_equity = portfolio.current_balance + unrealized_pnl
        
        return {
            "username": portfolio.user.username or portfolio.user.email if portfolio.user else "Unknown User",
            "balance": round(portfolio.current_balance, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "total_equity": round(total_equity, 2),
            "open_positions": len(open_positions)
        }

    async def run_game_loop(self):
        """Main game loop that streams candle data and player stats."""
        db = SessionLocal()
        try:
            # 1. Fetch room from database
            room = self._get_room_from_db(db)
            if not room:
                await self.broadcast({"type": "error", "message": "Room not found"})
                return
            
            self.symbol = room.symbol
            self.status = room.status
            
            # 2. Wait for game to become ACTIVE if still WAITING
            while room.status == "WAITING":
                await self.broadcast({
                    "type": "waiting",
                    "message": "Waiting for opponent to join...",
                    "room": {
                        "id": room.id,
                        "status": room.status,
                        "symbol": room.symbol
                    }
                })
                await asyncio.sleep(2)
                db.refresh(room)
            
            # 3. Game is now ACTIVE - fetch candle data
            self.started_at = int(room.started_at.timestamp()) if room.started_at else None
            self.game_duration = room.duration_seconds or DEFAULT_GAME_DURATION
            
            min_max_query = db.query(
                func.min(Candle.timestamp),
                func.max(Candle.timestamp)
            ).filter(Candle.symbol == room.symbol).first()
            
            if not min_max_query or not min_max_query[0] or not min_max_query[1]:
                await self.broadcast({"type": "error", "message": f"No candle data for {room.symbol}"})
                return
            
            min_ts, max_ts = min_max_query
            
            # Ensure we have enough data for the game duration
            latest_possible_start = max_ts - timedelta(seconds=self.game_duration)
            
            if latest_possible_start < min_ts:
                await self.broadcast({
                    "type": "error", 
                    "message": f"Insufficient data for {self.game_duration}s game. Available: {max_ts - min_ts}"
                })
                return
                
            # Pick a random start time
            # Convert to unix timestamp for random selection
            min_unix = int(min_ts.timestamp())
            max_unix = int(latest_possible_start.timestamp())
            
            random_start_unix = random.randint(min_unix, max_unix)
            from datetime import datetime, timezone
            scenario_start = datetime.fromtimestamp(random_start_unix, tz=timezone.utc).replace(tzinfo=None) # naive if db is naive

            # Fetch relevant candles (preload + game duration)
            # We fetch a bit more than needed to be safe
            needed_candles = self.game_duration + PRELOAD_CANDLES
            
            candles = db.query(Candle).filter(
                Candle.symbol == room.symbol,
                Candle.timestamp >= scenario_start
            ).order_by(Candle.timestamp).limit(needed_candles).all()
            
            if not candles:
                await self.broadcast({"type": "error", "message": f"Failed to fetch candles starting at {scenario_start}"})
                return

            # 4. Send 50 preload candles immediately (historical data)
            preload_data = []
            preload_count = min(PRELOAD_CANDLES, len(candles))
            for i in range(preload_count):
                candle = candles[i]
                preload_data.append({
                    "time": int(candle.timestamp.timestamp()),
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume
                })
            
            # Refresh room for latest portfolio data
            room = self._get_room_from_db(db)
            player_stats = self._build_player_stats(room, candles[preload_count - 1].close if preload_count > 0 else 0)
            
            await self.broadcast({
                "type": "game_start",
                "room": {
                    "id": room.id,
                    "status": room.status,
                    "symbol": room.symbol,
                    "started_at": self.started_at,
                    "game_duration": self.game_duration
                },
                "preload_candles": preload_data,
                "players": player_stats
            })
            
            # 5. Stream remaining candles at 1/second
            start_time = asyncio.get_event_loop().time()
            
            for i in range(preload_count, len(candles)):
                if not self.is_running or not self.active_connections:
                    break
                
                candle = candles[i]
                current_price = candle.close
                self.last_price = current_price
                
                # Refresh room to get latest position data
                db.expire_all()
                room = self._get_room_from_db(db)
                
                elapsed_time = asyncio.get_event_loop().time() - start_time
                time_remaining = max(0, self.game_duration - int(elapsed_time))
                
                # Check if game should end
                if time_remaining <= 0:
                    from datetime import datetime, timezone
                    room.status = "FINISHED"
                    room.ended_at = datetime.now(timezone.utc)
                    db.commit()
                    
                    player_stats = self._build_player_stats(room, current_price)
                    await self.broadcast({
                        "type": "game_end",
                        "room": {
                            "id": room.id,
                            "status": "FINISHED"
                        },
                        "final_stats": player_stats,
                        "winner": self._determine_winner(player_stats)
                    })
                    break
                
                # Build game update message
                player_stats = self._build_player_stats(room, current_price)
                
                await self.broadcast({
                    "type": "game_update",
                    "room": {
                        "id": room.id,
                        "status": room.status,
                        "time_remaining": time_remaining
                    },
                    "candle": {
                        "time": int(candle.timestamp.timestamp()),
                        "open": candle.open,
                        "high": candle.high,
                        "low": candle.low,
                        "close": candle.close,
                        "volume": candle.volume
                    },
                    "current_price": current_price,
                    "players": player_stats
                })
                
                await asyncio.sleep(1)  # 1 second per candle
                
        except Exception as e:
            print(f"Game loop error for room {self.room_id}: {e}")
            await self.broadcast({"type": "error", "message": str(e)})
        finally:
            db.close()
            self.is_running = False

    def _build_player_stats(self, room: Room, current_price: float) -> dict:
        """Build stats dict for both players."""
        stats = {}
        
        for portfolio in room.portfolios:
            if portfolio.user_id == room.player1_id:
                stats["player1"] = self._calculate_player_stats(portfolio, current_price)
            elif portfolio.user_id == room.player2_id:
                stats["player2"] = self._calculate_player_stats(portfolio, current_price)
        
        return stats

    def _determine_winner(self, player_stats: dict) -> Optional[dict]:
        """Determine the winner based on total equity."""
        p1 = player_stats.get("player1")
        p2 = player_stats.get("player2")
        
        if not p1 or not p2:
            return None
        
        if p1["total_equity"] > p2["total_equity"]:
            return {"username": p1["username"], "position": "player1"}
        elif p2["total_equity"] > p1["total_equity"]:
            return {"username": p2["username"], "position": "player2"}
        else:
            return {"tie": True}

    def get_current_price(self) -> float:
        """Get the current price for trade execution."""
        if self.last_price:
            return self.last_price
        
        # Fallback to DB fetch for latest price
        db = SessionLocal()
        try:
            if self.symbol:
                last_candle = db.query(Candle).filter(
                    Candle.symbol == self.symbol
                ).order_by(Candle.timestamp.desc()).first()
                if last_candle:
                    return last_candle.close
            return 0.0
        finally:
            db.close()


class RoomManager:
    """Manages all active game rooms."""
    
    def __init__(self):
        self.rooms: Dict[int, GameRoom] = {}

    def get_or_create_room(self, room_id: int, symbol: str = None) -> GameRoom:
        """Get existing room or create a new one."""
        if room_id not in self.rooms:
            self.rooms[room_id] = GameRoom(room_id)
        return self.rooms[room_id]
    
    def get_room(self, room_id: int) -> Optional[GameRoom]:
        """Get room if it exists."""
        return self.rooms.get(room_id)
        
    def get_current_price(self, room_id: int, symbol: str = None) -> float:
        """Get current price for a room."""
        room = self.get_or_create_room(room_id, symbol)
        return room.get_current_price()


# Global singleton
market_service = RoomManager()
