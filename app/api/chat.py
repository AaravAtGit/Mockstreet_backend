import asyncio
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from jose import jwt, JWTError
from sqlalchemy.orm import Session
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.models.room import Room
from app.models.portfolio import Portfolio

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


class ChatConnection:
    """Represents a single chat connection."""
    
    def __init__(self, websocket: WebSocket, user_id: int, username: str, room_id: int):
        self.websocket = websocket
        self.user_id = user_id
        self.username = username
        self.room_id = room_id


class ChatRoom:
    """Manages chat connections for a single room."""
    
    def __init__(self, room_id: int):
        self.room_id = room_id
        self.connections: List[ChatConnection] = []
        self.message_history: List[dict] = []
        self.max_history = 50  # Keep last 50 messages
    
    def add_connection(self, conn: ChatConnection):
        self.connections.append(conn)
    
    def remove_connection(self, conn: ChatConnection):
        self.connections = [c for c in self.connections if c != conn]
    
    async def broadcast(self, message: dict, exclude: Optional[ChatConnection] = None):
        """Send message to all connections except excluded one."""
        self.message_history.append(message)
        if len(self.message_history) > self.max_history:
            self.message_history = self.message_history[-self.max_history:]
        
        dead_connections = []
        for conn in self.connections:
            if conn == exclude:
                continue
            try:
                await conn.websocket.send_json(message)
            except Exception:
                dead_connections.append(conn)
        
        for dead in dead_connections:
            self.remove_connection(dead)
    
    async def send_history(self, conn: ChatConnection):
        """Send message history to a new connection."""
        for msg in self.message_history:
            await conn.websocket.send_json(msg)


class ChatManager:
    """Manages all chat rooms."""
    
    def __init__(self):
        self.rooms: Dict[int, ChatRoom] = {}
    
    def get_or_create_room(self, room_id: int) -> ChatRoom:
        if room_id not in self.rooms:
            self.rooms[room_id] = ChatRoom(room_id)
        return self.rooms[room_id]


chat_manager = ChatManager()


@router.websocket("/ws/chat/{room_id}")
async def chat_websocket(websocket: WebSocket, room_id: int):
    """
    Chat WebSocket endpoint for in-game messaging.
    
    Authentication: Send first message with {"type": "auth", "token": "jwt_token"}
    
    Send messages: {"message": "Hello!"}
    
    Receive messages:
    {
        "type": "chat_message",
        "username": "player1@example.com",
        "message": "Hello!",
        "timestamp": 1703289601
    }
    
    System messages (joins/leaves):
    {
        "type": "system",
        "message": "player1@example.com joined the chat",
        "timestamp": 1703289601
    }
    """
    await websocket.accept()
    conn = None
    
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
            username = user.username or user.email
        finally:
            db.close()
        
        # Authentication successful
        await websocket.send_json({
            "type": "auth_success",
            "username": username,
            "room_id": room_id
        })
        
        # Add to chat room
        chat_room = chat_manager.get_or_create_room(room_id)
        conn = ChatConnection(websocket, user_id, username, room_id)
        chat_room.add_connection(conn)
        
        # Send message history
        await chat_room.send_history(conn)
        
        # Announce join
        join_msg = {
            "type": "system",
            "message": f"{username} joined the chat",
            "timestamp": int(datetime.now(timezone.utc).timestamp())
        }
        await chat_room.broadcast(join_msg)
        
        # Listen for messages
        while True:
            data = await websocket.receive_json()
            
            if "message" in data and data["message"].strip():
                chat_msg = {
                    "type": "chat_message",
                    "username": username,
                    "message": data["message"].strip()[:500],  # Limit message length
                    "timestamp": int(datetime.now(timezone.utc).timestamp())
                }
                await chat_room.broadcast(chat_msg)
            
    except asyncio.TimeoutError:
        await websocket.send_json({
            "type": "error",
            "message": "Authentication timeout"
        })
        await websocket.close(code=4002)
    except WebSocketDisconnect:
        pass
    finally:
        if conn:
            chat_room = chat_manager.get_or_create_room(room_id)
            chat_room.remove_connection(conn)
            
            # Announce leave
            leave_msg = {
                "type": "system",
                "message": f"{conn.username} left the chat",
                "timestamp": int(datetime.now(timezone.utc).timestamp())
            }
            await chat_room.broadcast(leave_msg)
