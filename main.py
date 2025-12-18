from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.api.users import router as users_router
from app.api.candles import router as candles_router

app = FastAPI(
    title="Trading Battles Platform",
    description="Backend for a real-time trading battles platform.",
    version="0.1.0",
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)