# Trading Battles API Documentation

A comprehensive backend for the Trading Battles platform - a real-time competitive trading game where two players battle head-to-head to generate the highest profit.

---

## Table of Contents

1. [Overview](#overview)
2. [Base URL & Setup](#base-url--setup)
3. [Authentication](#authentication)
4. [Rooms (Game Sessions)](#rooms-game-sessions)
5. [Trading Engine](#trading-engine)
6. [Real-time WebSockets](#real-time-websockets)
7. [Error Handling](#error-handling)
8. [Developer Setup](#developer-setup)

---

## Overview

### How the Game Works

1. **Player 1** creates a room, selecting a trading symbol (e.g., AAPL, BTCUSD) and game duration
2. **Player 2** joins the room - this starts the game timer
3. Both players receive **$100,000 virtual cash** and compete to generate the highest profit
4. Players can open **LONG** (buy) or **SHORT** (sell) positions with leverage
5. Live candle data streams every second, updating position PnL in real-time
6. When the timer expires, the player with the **highest total equity** (balance + unrealized PnL) wins

### Key Features

- Real-time price streaming via WebSockets
- Server-side PnL calculation (secure, no tampering)
- Multiple position support (hedging allowed)
- Leverage trading (1x to 100x)
- In-game chat between players

---

## Base URL & Setup

```
Production: https://api.mockstreet.com
Development: http://localhost:8000
```

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt
pip install websockets

# Run server
uvicorn main:app --reload

# Server runs at http://localhost:8000
# API docs at http://localhost:8000/docs
```

---

## Authentication

All game endpoints require a **Bearer Token** in the Authorization header.

### 1. Register a New User

Creates a new user account.

**Endpoint:** `POST /register`

**Request Body:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email` | string | Yes | Valid email address (must be unique) |
| `password` | string | Yes | User password (stored hashed) |

**Example Request:**
```json
{
  "email": "player1@example.com",
  "username": "player1",
  "password": "securepassword123"
}
```

**Success Response (200 OK):**
```json
{
  "email": "player1@example.com",
  "username": "player1",
  "is_active": true,
  "is_verified": false
}
```

| Field | Type | Description |
|-------|------|-------------|
| `email` | string | User's email address |
| `username` | string | User's username |
| `is_active` | boolean | Whether account is active |
| `is_verified` | boolean | Whether email is verified |

**Error Responses:**
| Status | Detail | Cause |
|--------|--------|-------|
| 400 | "Email already registered" | Email already exists in database |
| 400 | "Username already taken" | Username already exists in database |
| 422 | Validation Error | Invalid email format or missing fields |

---

### 2. Check Username Existence

Checks if a username is already taken.

**Endpoint:** `GET /check-username/{username}`

**URL Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `username` | string | Yes | Username to check |

**Example Request:**
```bash
curl "http://localhost:8000/check-username/player1"
```

**Success Response (200 OK):**
```json
{
  "exists": true
}
```

---

### 3. Get Current User Info

Retrieves the authenticated user's profile info.

**Endpoint:** `GET /me`

**Headers:**
```
Authorization: Bearer <your_token>
```

**Success Response (200 OK):**
```json
{
  "email": "player1@example.com",
  "username": "player1",
  "is_active": true,
  "is_verified": true
}
```

---

### 4. Login

Authenticates a user and returns a JWT access token.

**Endpoint:** `POST /login`

**Content-Type:** `application/x-www-form-urlencoded` (Form Data)

**Request Body (Form Data):**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `username` | string | Yes | User's email address |
| `password` | string | Yes | User's password |

**Example Request (cURL):**
```bash
curl -X POST "http://localhost:8000/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=player1@example.com&password=securepassword123"
```

**Success Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJwbGF5ZXIxQGV4YW1wbGUuY29tIiwiZXhwIjoxNzAzMjg5NjAwfQ.abc123",
  "token_type": "bearer"
}
```

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | JWT token for authentication |
| `token_type` | string | Always "bearer" |

**Using the Token:**
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Error Responses:**
| Status | Detail | Cause |
|--------|--------|-------|
| 401 | "Incorrect username or password" | Wrong email or password |
| 422 | Validation Error | Missing username or password field |

---

### 5. Verify Email

Verifies user's email address using a token sent via email.

**Endpoint:** `GET /verify-mail/{token}`

**URL Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `token` | string | Yes | Email verification token from email link |

**Success Response (200 OK):**
```json
{
  "message": "Email verified"
}
```

**Error Responses:**
| Status | Detail | Cause |
|--------|--------|-------|
| 400 | "Invalid token" | Token is malformed |
| 401 | "Invalid token" | Token expired or invalid signature |
| 404 | "User not found" | User associated with token doesn't exist |

---

## Rooms (Game Sessions)

Rooms are game sessions where two players compete. Each room has a specific trading symbol and duration.

### Room Status Flow

```
WAITING → ACTIVE → FINISHED
   ↑         ↑         ↑
Created  Player2   Timer
         Joins     Expires
```

| Status | Description |
|--------|-------------|
| `WAITING` | Room created, waiting for second player |
| `ACTIVE` | Both players joined, game in progress |
| `FINISHED` | Game ended, winner determined |

---

### 1. Create a Room

Creates a new game room. The creator becomes Player 1.

**Endpoint:** `POST /rooms/`

**Headers:**
```
Authorization: Bearer <your_token>
```

**Request Body:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | string | Yes | - | Display name for the room |
| `symbol` | string | Yes | - | Trading symbol (e.g., "AAPL", "BTCUSD") |
| `duration_seconds` | integer | No | 1800 | Game duration in seconds (60-3600) |

**Duration Options:**
| Seconds | Human Readable |
|---------|----------------|
| 60 | 1 minute (minimum) |
| 300 | 5 minutes |
| 600 | 10 minutes |
| 1800 | 30 minutes (default) |
| 3600 | 60 minutes (maximum) |

**Example Request:**
```json
{
  "name": "AAPL Speed Battle",
  "symbol": "AAPL",
  "duration_seconds": 600
}
```

**Success Response (200 OK):**
```json
{
  "id": 1,
  "name": "AAPL Speed Battle",
  "symbol": "AAPL",
  "status": "WAITING",
  "player1_username": "player1",
  "player2_username": null,
  "created_at": "2025-12-27T10:00:00.000000",
  "started_at": null,
  "ended_at": null,
  "duration_seconds": 600
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique room identifier (use for WebSocket connections) |
| `name` | string | Room display name |
| `symbol` | string | Trading symbol for this game |
| `status` | string | Current room status |
| `player1_username` | string | Username of room creator |
| `player2_username` | string/null | Username of opponent (null until joined) |
| `created_at` | datetime | When room was created |
| `started_at` | datetime/null | When game started (player2 joined) |
| `ended_at` | datetime/null | When game ended |
| `duration_seconds` | integer | Game length in seconds |

**Error Responses:**
| Status | Detail | Cause |
|--------|--------|-------|
| 401 | "Could not validate credentials" | Missing or invalid token |

---

### 2. Join a Room

Join an existing room. Joining starts the game (sets status to ACTIVE).

**Endpoint:** `POST /rooms/{room_id}/join`

**Headers:**
```
Authorization: Bearer <your_token>
```

**URL Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `room_id` | integer | Yes | ID of the room to join |

**Example Request:**
```bash
curl -X POST "http://localhost:8000/rooms/1/join" \
  -H "Authorization: Bearer <your_token>"
```

**Success Response (200 OK):**
```json
{
  "id": 1,
  "name": "AAPL Speed Battle",
  "symbol": "AAPL",
  "status": "ACTIVE",
  "player1_username": "player1",
  "player2_username": "player2",
  "created_at": "2025-12-27T10:00:00.000000",
  "started_at": "2025-12-27T10:01:30.000000",
  "ended_at": null,
  "duration_seconds": 600
}
```

**Note:** When you join:
- `status` changes from `WAITING` to `ACTIVE`
- `started_at` is set to the current time (game timer begins)
- Your portfolio is automatically created with $100,000

**Error Responses:**
| Status | Detail | Cause |
|--------|--------|-------|
| 400 | "Room is not accepting new players" | Room status is not WAITING |
| 400 | "You are already in this room" | You are player1 |
| 401 | "Could not validate credentials" | Missing or invalid token |
| 404 | "Room not found" | Room ID doesn't exist |

---

### 3. List All Rooms

Retrieve a list of all rooms.

**Endpoint:** `GET /rooms/`

**Query Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `skip` | integer | No | 0 | Number of rooms to skip (pagination) |
| `limit` | integer | No | 100 | Maximum rooms to return |

**Example Request:**
```bash
curl "http://localhost:8000/rooms/?skip=0&limit=10"
```

**Success Response (200 OK):**
```json
[
  {
    "id": 1,
    "name": "AAPL Speed Battle",
    "symbol": "AAPL",
    "status": "ACTIVE",
    "player1_username": "player1",
    "player2_username": "player2",
    "created_at": "2025-12-27T10:00:00.000000",
    "started_at": "2025-12-27T10:01:30.000000",
    "ended_at": null,
    "duration_seconds": 600
  },
  {
    "id": 2,
    "name": "BTC Arena",
    "symbol": "BTCUSD",
    "status": "WAITING",
    "player1_username": "player3",
    "player2_username": null,
    "created_at": "2025-12-27T10:05:00.000000",
    "started_at": null,
    "ended_at": null,
    "duration_seconds": 1800
  }
]
```

---

## Trading Engine

Execute trades and manage positions within a game room.

### Position Mechanics

| Concept | Description |
|---------|-------------|
| **LONG** | Profit when price goes UP |
| **SHORT** | Profit when price goes DOWN |
| **Leverage** | Multiply your position size (and risk) |
| **Margin** | Cash required = (Price × Quantity) / Leverage |
| **PnL** | (Current Price - Entry Price) × Quantity × Direction × Leverage |

---

### 1. Get Portfolio

Retrieve your portfolio for a specific room, including balance and open positions.

**Endpoint:** `GET /game/portfolio`

**Headers:**
```
Authorization: Bearer <your_token>
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `room_id` | integer | Yes | The room ID to get portfolio for |

**Example Request:**
```bash
curl "http://localhost:8000/game/portfolio?room_id=1" \
  -H "Authorization: Bearer <your_token>"
```

**Success Response (200 OK):**
```json
{
  "id": 5,
  "username": "player1",
  "room_id": 1,
  "initial_balance": 100000.0,
  "current_balance": 95000.0,
  "positions": [
    {
      "id": 101,
      "portfolio_id": 5,
      "side": "LONG",
      "quantity": 10.0,
      "leverage": 10,
      "entry_price": 150.25,
      "entry_time": "2025-12-27T10:05:00.000000",
      "exit_price": null,
      "exit_time": null,
      "is_open": true,
      "pnl": null
    },
    {
      "id": 102,
      "portfolio_id": 5,
      "side": "SHORT",
      "quantity": 5.0,
      "leverage": 5,
      "entry_price": 151.00,
      "entry_time": "2025-12-27T10:07:00.000000",
      "exit_price": 150.50,
      "exit_time": "2025-12-27T10:08:00.000000",
      "is_open": false,
      "pnl": 12.50
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Portfolio ID |
| `username` | string | Your username |
| `room_id` | integer | Room this portfolio belongs to |
| `initial_balance` | float | Starting balance ($100,000) |
| `current_balance` | float | Available cash (after margin deductions) |
| `positions` | array | List of all positions (open and closed) |

**Position Object Fields:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique position ID (use for closing) |
| `side` | string | "LONG" or "SHORT" |
| `quantity` | float | Number of units |
| `leverage` | integer | Position leverage multiplier |
| `entry_price` | float | Price when position was opened |
| `entry_time` | datetime | When position was opened |
| `exit_price` | float/null | Price when closed (null if open) |
| `exit_time` | datetime/null | When closed (null if open) |
| `is_open` | boolean | Whether position is still active |
| `pnl` | float/null | Realized profit/loss (null if open) |

**Error Responses:**
| Status | Detail | Cause |
|--------|--------|-------|
| 401 | "Could not validate credentials" | Missing or invalid token |
| 404 | "Portfolio not found for this room" | You haven't joined this room |

---

### 2. Place Trade (Open Position)

Open a new trading position.

**Endpoint:** `POST /game/trade`

**Headers:**
```
Authorization: Bearer <your_token>
```

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `room_id` | integer | Yes | The room to trade in |

**Request Body:**
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `side` | string | Yes | - | "LONG" (buy) or "SHORT" (sell) |
| `quantity` | float | Yes | - | Number of units to trade |
| `leverage` | integer | No | 1 | Leverage multiplier (1-100) |

**Margin Calculation:**
```
Margin Required = (Current Price × Quantity) / Leverage

Example: Price=$150, Quantity=10, Leverage=10
Margin = ($150 × 10) / 10 = $150
```

**Example Request:**
```json
{
  "side": "LONG",
  "quantity": 10.0,
  "leverage": 10
}
```

**Success Response (200 OK):**
```json
{
  "id": 103,
  "portfolio_id": 5,
  "side": "LONG",
  "quantity": 10.0,
  "leverage": 10,
  "entry_price": 150.50,
  "entry_time": "2025-12-27T10:10:00.000000",
  "exit_price": null,
  "exit_time": null,
  "is_open": true,
  "pnl": null
}
```

**Error Responses:**
| Status | Detail | Cause |
|--------|--------|-------|
| 400 | "Game not active. Waiting for players." | Room status is not ACTIVE |
| 400 | "Insufficient funds" | Not enough balance for margin |
| 401 | "Could not validate credentials" | Missing or invalid token |
| 404 | "Portfolio not found" | You haven't joined this room |
| 404 | "Room not found" | Room doesn't exist |
| 500 | "Market data unavailable" | No price data for symbol |

---

### 3. Close Trade

Close an open position and realize profit/loss.

**Endpoint:** `POST /game/close/{position_id}`

**Headers:**
```
Authorization: Bearer <your_token>
```

**URL Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `position_id` | integer | Yes | ID of position to close |

**Example Request:**
```bash
curl -X POST "http://localhost:8000/game/close/103" \
  -H "Authorization: Bearer <your_token>"
```

**Success Response (200 OK):**
```json
{
  "id": 103,
  "portfolio_id": 5,
  "side": "LONG",
  "quantity": 10.0,
  "leverage": 10,
  "entry_price": 150.50,
  "entry_time": "2025-12-27T10:10:00.000000",
  "exit_price": 152.00,
  "exit_time": "2025-12-27T10:15:00.000000",
  "is_open": false,
  "pnl": 150.0
}
```

**PnL Calculation:**
```
Direction = 1 (LONG) or -1 (SHORT)
PnL = (Exit Price - Entry Price) × Quantity × Direction × Leverage

Example LONG: Entry=$150.50, Exit=$152.00, Qty=10, Leverage=10
PnL = ($152.00 - $150.50) × 10 × 1 × 10 = $150.00
```

**After closing:**
- Original margin is returned to your balance
- PnL is added to (or subtracted from) your balance

**Error Responses:**
| Status | Detail | Cause |
|--------|--------|-------|
| 400 | "Position already closed" | Position is_open is already false |
| 401 | "Could not validate credentials" | Missing or invalid token |
| 404 | "Position not found" | Position doesn't exist or you don't own it |
| 500 | "Market data unavailable" | No price data for symbol |

---

## Real-time WebSockets

Three WebSocket endpoints provide real-time data during games.

### Connection Overview

| Endpoint | Authentication | Purpose |
|----------|----------------|---------|
| `/ws/game/{room_id}` | None (Public) | Game state, candles, all player stats |
| `/ws/portfolio/{room_id}` | First-message JWT | Your private position details |
| `/ws/chat/{room_id}` | First-message JWT | In-game messaging |

---

### 1. Game WebSocket (Public)

Stream live game data including candles, both players' stats, and game status.

**Endpoint:** `WS /ws/game/{room_id}`

**URL Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `room_id` | integer | Yes | Room ID to connect to |

**Connection Example (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/game/1');

ws.onopen = () => {
  console.log('Connected to game');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Game update:', data);
};

ws.onclose = () => {
  console.log('Disconnected');
};
```

**Message Types:**

#### Type: `waiting`
Sent repeatedly while waiting for second player to join.

```json
{
  "type": "waiting",
  "message": "Waiting for opponent to join...",
  "room": {
    "id": 1,
    "status": "WAITING",
    "symbol": "AAPL"
  }
}
```

#### Type: `game_start`
Sent once when the game begins. Includes 50 preload candles for chart history.

```json
{
  "type": "game_start",
  "room": {
    "id": 1,
    "status": "ACTIVE",
    "symbol": "AAPL",
    "started_at": 1703677290,
    "game_duration": 600
  },
  "preload_candles": [
    {
      "time": 1703677200,
      "open": 150.00,
      "high": 150.50,
      "low": 149.80,
      "close": 150.25,
      "volume": 10000
    },
    // ... 49 more candles
  ],
  "players": {
    "player1": {
      "username": "player1",
      "balance": 100000.0,
      "unrealized_pnl": 0.0,
      "total_equity": 100000.0,
      "open_positions": 0
    },
    "player2": {
      "username": "player2",
      "balance": 100000.0,
      "unrealized_pnl": 0.0,
      "total_equity": 100000.0,
      "open_positions": 0
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `room.started_at` | integer | Unix timestamp when game started |
| `room.game_duration` | integer | Total game length in seconds |
| `preload_candles` | array | 50 historical candles for chart |
| `players.playerX.balance` | float | Available cash |
| `players.playerX.unrealized_pnl` | float | PnL from open positions |
| `players.playerX.total_equity` | float | balance + unrealized_pnl |
| `players.playerX.open_positions` | integer | Number of open positions |

#### Type: `game_update`
Sent every second during active gameplay.

```json
{
  "type": "game_update",
  "room": {
    "id": 1,
    "status": "ACTIVE",
    "time_remaining": 540
  },
  "candle": {
    "time": 1703677350,
    "open": 150.25,
    "high": 150.60,
    "low": 150.20,
    "close": 150.55,
    "volume": 1500
  },
  "current_price": 150.55,
  "players": {
    "player1": {
      "username": "player1",
      "balance": 95000.0,
      "unrealized_pnl": 550.0,
      "total_equity": 95550.0,
      "open_positions": 2
    },
    "player2": {
      "username": "player2",
      "balance": 98000.0,
      "unrealized_pnl": -200.0,
      "total_equity": 97800.0,
      "open_positions": 1
    }
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `room.time_remaining` | integer | Seconds left in game |
| `candle` | object | OHLCV candle data for this second |
| `current_price` | float | Latest close price |

#### Type: `game_end`
Sent when the game timer expires.

```json
{
  "type": "game_end",
  "room": {
    "id": 1,
    "status": "FINISHED"
  },
  "final_stats": {
    "player1": {
      "username": "player1",
      "balance": 95000.0,
      "unrealized_pnl": 6200.0,
      "total_equity": 101200.0,
      "open_positions": 2
    },
    "player2": {
      "username": "player2",
      "balance": 98000.0,
      "unrealized_pnl": 500.0,
      "total_equity": 98500.0,
      "open_positions": 1
    }
  },
  "winner": {
    "username": "player1",
    "position": "player1"
  }
}
```

**Winner Object:**
| Value | Description |
|-------|-------------|
| `{"username": "player1", "position": "player1"}` | Player 1 wins |
| `{"username": "player2", "position": "player2"}` | Player 2 wins |
| `{"tie": true}` | Both players have equal equity |

#### Type: `error`
Sent when an error occurs.

```json
{
  "type": "error",
  "message": "Room not found"
}
```

---

### 2. Portfolio WebSocket (Private, Authenticated)

Stream your private position details with real-time PnL calculations.

**Endpoint:** `WS /ws/portfolio/{room_id}`

**Authentication:** Send auth message as first message after connecting.

**Connection Example (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/portfolio/1');

ws.onopen = () => {
  // REQUIRED: Send auth message first
  ws.send(JSON.stringify({
    type: "auth",
    token: "your_jwt_token_here"
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'auth_success') {
    console.log('Authenticated successfully');
  } else if (data.type === 'portfolio_update') {
    console.log('Portfolio:', data);
  } else if (data.type === 'error') {
    console.error('Error:', data.message);
  }
};
```

**Auth Request (must be first message):**
```json
{
  "type": "auth",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Auth Success Response:**
```json
{
  "type": "auth_success",
  "username": "player1",
  "room_id": 1
}
```

**Auth Error Responses:**
| Response | Cause |
|----------|-------|
| `{"type": "error", "message": "Expected auth message..."}` | First message wasn't auth type |
| `{"type": "error", "message": "Invalid or expired token"}` | JWT is invalid |
| `{"type": "error", "message": "You are not in this room"}` | User hasn't joined this room |
| `{"type": "error", "message": "Authentication timeout"}` | No auth message within 10 seconds |

**Portfolio Update (sent every second after auth):**
```json
{
  "type": "portfolio_update",
  "balance": 95000.0,
  "unrealized_pnl": 550.0,
  "total_equity": 95550.0,
  "current_price": 150.55,
  "positions": [
    {
      "id": 101,
      "side": "LONG",
      "quantity": 10.0,
      "leverage": 10,
      "entry_price": 150.00,
      "current_price": 150.55,
      "unrealized_pnl": 55.0,
      "entry_time": "2025-12-27T10:05:00.000000"
    },
    {
      "id": 102,
      "side": "SHORT",
      "quantity": 5.0,
      "leverage": 5,
      "entry_price": 151.00,
      "current_price": 150.55,
      "unrealized_pnl": 11.25,
      "entry_time": "2025-12-27T10:07:00.000000"
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `balance` | float | Your available cash |
| `unrealized_pnl` | float | Total PnL from all open positions |
| `total_equity` | float | balance + unrealized_pnl |
| `current_price` | float | Latest market price |
| `positions` | array | Your open positions with live PnL |

**Position Object:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Position ID (use for closing) |
| `side` | string | "LONG" or "SHORT" |
| `quantity` | float | Position size |
| `leverage` | integer | Leverage multiplier |
| `entry_price` | float | Price when opened |
| `current_price` | float | Current market price |
| `unrealized_pnl` | float | Current profit/loss for this position |
| `entry_time` | string | When position was opened |

---

### 3. Chat WebSocket (Private, Authenticated)

Real-time messaging between players during the game.

**Endpoint:** `WS /ws/chat/{room_id}`

**Authentication:** Same as Portfolio WebSocket - send auth message first.

**Connection Example (JavaScript):**
```javascript
const ws = new WebSocket('ws://localhost:8000/ws/chat/1');

ws.onopen = () => {
  ws.send(JSON.stringify({
    type: "auth",
    token: "your_jwt_token_here"
  }));
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  
  if (data.type === 'chat_message') {
    console.log(`${data.username}: ${data.message}`);
  } else if (data.type === 'system') {
    console.log(`[SYSTEM] ${data.message}`);
  }
};

// Send a message (after authenticated)
function sendMessage(text) {
  ws.send(JSON.stringify({ message: text }));
}
```

**Auth Request (must be first message):**
```json
{
  "type": "auth",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Auth Success Response:**
```json
{
  "type": "auth_success",
  "username": "player1",
  "room_id": 1
}
```

**Send a Chat Message:**
```json
{
  "message": "Nice trade!"
}
```

*Note: Messages are limited to 500 characters.*

**Receive Chat Message:**
```json
{
  "type": "chat_message",
  "username": "player1@example.com",
  "message": "Nice trade!",
  "timestamp": 1703677400
}
```

| Field | Type | Description |
|-------|------|-------------|
| `username` | string | Email of message sender |
| `message` | string | Message content |
| `timestamp` | integer | Unix timestamp when sent |

**System Messages (join/leave):**
```json
{
  "type": "system",
  "message": "player1@example.com joined the chat",
  "timestamp": 1703677350
}
```

```json
{
  "type": "system",
  "message": "player2@example.com left the chat",
  "timestamp": 1703677600
}
```

**Message History:** When you connect, you receive the last 50 messages automatically.

---

## Error Handling

### HTTP Error Format

All HTTP errors return JSON in this format:

```json
{
  "detail": "Error message here"
}
```

### Common HTTP Status Codes

| Status | Meaning | Common Causes |
|--------|---------|---------------|
| 200 | Success | Request completed successfully |
| 400 | Bad Request | Invalid input, business logic violation |
| 401 | Unauthorized | Missing or invalid authentication token |
| 404 | Not Found | Resource doesn't exist |
| 422 | Validation Error | Request body missing required fields |
| 500 | Server Error | Internal error (e.g., no market data) |

### WebSocket Close Codes

| Code | Meaning |
|------|---------|
| 4001 | Invalid auth message format |
| 4002 | Authentication timeout (10 seconds) |
| 4003 | Invalid or expired token |
| 4004 | User not in this room |

---

## Developer Setup

### Prerequisites

- Python 3.10+
- pip
- Virtual environment (recommended)

### Installation

```bash
# Clone repository
git clone <repo-url>
cd backend

# Create virtual environment
python -m venv .env
source .env/bin/activate  # Linux/Mac
# or
.env\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt
pip install websockets  # Required for WebSocket support

# Run database migrations (if using Alembic)
alembic upgrade head
```

### Running the Server

```bash
# Development (with auto-reload)
uvicorn main:app --reload

# Production
uvicorn main:app --host 0.0.0.0 --port 8000
```

### API Documentation (Swagger)

Once running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

### Testing

```bash
# Unit tests
python scripts/test_api.py

# Test WebSocket manually (browser console)
const ws = new WebSocket('ws://localhost:8000/ws/game/1');
ws.onmessage = (e) => console.log(JSON.parse(e.data));
```

### Environment Variables

Create a `.env` file or set these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | (required) |
| `DATABASE_URL` | Database connection string | sqlite:///./app.db |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry time | 30 |

---

## Quick Reference

### Complete Game Flow

```bash
# 1. Register players
POST /register  →  Create player1@example.com
POST /register  →  Create player2@example.com

# 2. Login both players
POST /login  →  Get token for player1
POST /login  →  Get token for player2

# 3. Player1 creates room
POST /rooms/  →  Returns room_id: 1

# 4. Both connect to game WebSocket
WS /ws/game/1  →  Both players connect

# 5. Player2 joins room (starts game)
POST /rooms/1/join  →  Game becomes ACTIVE

# 6. Connect to private WebSockets
WS /ws/portfolio/1  →  Each player's positions
WS /ws/chat/1  →  In-game chat

# 7. Trade during game
POST /game/trade?room_id=1  →  Open positions
POST /game/close/{position_id}  →  Close positions

# 8. Game ends when timer expires
# Winner = highest total_equity
```
      