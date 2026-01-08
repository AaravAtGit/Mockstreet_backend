import logging

logging.basicConfig(level=logging.INFO)

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.api.users import router as users_router

from app.api.candles import router as candles_router
from app.api.rooms import router as rooms_router
from app.api.game import router as game_router
from app.api.game_ws import router as game_ws_router
from app.api.chat import router as chat_router

app = FastAPI(
    title="Trading Battles Platform",
    description="Backend for a real-time trading battles platform.",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", tags=["Root"])
async def read_root():
    return {"message": "Welcome to the Trading Battles API!"}

@app.get("/chart", tags=["Frontend"])
async def get_chart():
    return FileResponse('static/index.html')

app.include_router(users_router, tags=["users"])

app.include_router(candles_router, tags=["candles"])
app.include_router(rooms_router, prefix="/rooms", tags=["rooms"])
app.include_router(game_router, prefix="/game", tags=["game"])
app.include_router(game_ws_router, tags=["websocket"])
app.include_router(chat_router, tags=["chat"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

