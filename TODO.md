# Trading Battles Implementation TODOs

Current Status: Core game mechanics, trading engine, and real-time WebSockets are implemented. The platform supports user authentication, room creation/joining, and real-time battle tracking.

## 1. Database Models (SQLAlchemy) [DONE]
Ref: `app/models/`
- [x] **Room Model**: To manage game sessions.
- [x] **Portfolio Model**: To track player state within a specific room.
- [x] **Position Model**: To track active trades (Hedging Mode).
- [ ] **Trade History Model**: To record all actions. (Partial/Position based)

## 2. Pydantic Schemas [DONE]
Ref: `app/schemas/`
- [x] **Room Schemas**: `RoomCreate`, `RoomResponse` (with players and status).
- [x] **Trade Schemas**: `TradeRequest`, `PositionResponse`.
- [x] **Portfolio Schemas**: `PortfolioResponse` (balance, equity, open_positions).

## 3. API Endpoints [DONE]
Ref: `app/api/`
- [x] **Rooms Router** (`/rooms`):
    - `POST /` - Create a new battle room.
    - `POST /{room_id}/join` - Join an existing room.
    - `GET /` - List available rooms.
- [x] **Game Router** (`/game`):
    - `POST /trade` - Execute a trade (buy/sell).
    - `GET /portfolio` - Get current stats (Cash, Unrealized PnL, Total Equity).

## 4. Game Logic & Trading Engine [DONE]
Ref: `app/core/`
- [x] **PnL Calculation**: Implement formula.
- [x] **Margin Check**: Ensure user has enough balance to open position.
- [x] **Hedging Support**: treated as separate positions.
- [x] **Win Condition**: Calculate Total Equity and compare players.

## 5. Real-time [DONE]
- [x] **WebSockets**:
    - Stream live portfolio updates.
    - Stream live game status (timer) and candle data.
    - In-game chat between players.
