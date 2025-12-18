from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.db.session import SessionLocal
from app.models.candle import Candle
import asyncio
import json

router = APIRouter()

class GameRoom:
    def __init__(self, room_id: str, symbol: str):
        self.room_id = room_id
        self.symbol = symbol
        self.active_connections: List[WebSocket] = []
        self.history: List[dict] = [] 
        self.is_running = False
        self.task = None

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        
        # Send existing history so they catch up
        for data in self.history:
             await websocket.send_text(json.dumps(data))

        # If game not running, start it
        if not self.is_running:
            self.is_running = True
            self.task = asyncio.create_task(self.run_game_loop())

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        self.history.append(message)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                dead_connections.append(connection)
        
        for dead in dead_connections:
            self.disconnect(dead)

    async def run_game_loop(self):
        db = SessionLocal()
        try:
            candles = db.query(Candle).filter(Candle.symbol == self.symbol).order_by(Candle.timestamp).all()
            if not candles:
                await self.broadcast({"error": "No data found"})
                return

            for candle in candles:
                # If everyone left, we could stop, but for now let's keep running 
                # or check if we should pause. 
                # For simplicity, we run until end of data.
                
                data = {
                    "time": int(candle.timestamp.timestamp()),
                    "open": candle.open,
                    "high": candle.high,
                    "low": candle.low,
                    "close": candle.close,
                    "volume": candle.volume
                }
                await self.broadcast(data)
                await asyncio.sleep(1)
        except Exception as e:
            print(f"Game loop error: {e}")
        finally:
            db.close()
            self.is_running = False

class RoomManager:
    def __init__(self):
        self.rooms: Dict[str, GameRoom] = {}

    def get_or_create_room(self, room_id: str, symbol: str) -> GameRoom:
        if room_id not in self.rooms:
            self.rooms[room_id] = GameRoom(room_id, symbol)
        # If the room exists but for a different symbol, we might want to handle that.
        # For now, we assume the room is tied to the symbol it was created with.
        return self.rooms[room_id]

manager = RoomManager()

@router.websocket("/candles/ws/{room_id}/{symbol}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, symbol: str):
    room = manager.get_or_create_room(room_id, symbol)
    await room.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        room.disconnect(websocket)

