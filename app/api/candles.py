from typing import List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.services.market_engine import market_service
from app.db.session import get_db
from app.models.candle import Candle

router = APIRouter()


@router.get("/tickers", response_model=List[str])
def get_available_tickers(db: Session = Depends(get_db)):
    """List all available trading pairs."""
    tickers = db.query(Candle.symbol).distinct().all()
    # tickers is a list of tuples like [('AAPL',), ('BTC-USD',)]
    return [t[0] for t in tickers]


@router.get("/ws/game/{room_id}")
async def websocket_info(room_id: int):
    """
    This endpoint is for WebSocket connections only.
    Use a WebSocket client to connect to ws://host/ws/game/{room_id}
    """
    return JSONResponse(
        status_code=400,
        content={
            "error": "This is a WebSocket endpoint",
            "message": f"Use a WebSocket client to connect to ws://host/ws/game/{room_id}",
            "room_id": room_id
        }
    ) 


@router.websocket("/ws/game/{room_id}")
async def game_websocket(websocket: WebSocket, room_id: int):
    """
    Public game WebSocket endpoint.

    Streams:
    - Room status (WAITING, ACTIVE, FINISHED)
    - 50 preload candles on game start
    - Real-time candle updates (1/second)
    - Both players' PnL and stats
    - Time remaining
    - Winner announcement on game end
    
    Message Types:
    - waiting: Game waiting for opponent
    - game_start: Game started with preload candles
    - game_update: Real-time candle + stats
    - game_end: Game finished with winner
    - error: Error occurred
    """
    room = market_service.get_or_create_room(room_id)
    await room.connect(websocket)
    try:
        while True:
            # Keep connection alive, handle any client messages if needed
            await websocket.receive_text()
    except WebSocketDisconnect:
        room.disconnect(websocket)



