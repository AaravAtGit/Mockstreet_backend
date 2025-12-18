import yfinance as yf
from app.db.session import SessionLocal
from app.models.candle import Candle

db = SessionLocal()

def fetch_data(symbol: str, start_date: str, end_date: str, interval: str = "1m"):

    data = yf.download(symbol, start=start_date, end=end_date, interval=interval)
    for index, row in data.iterrows():
        candle = Candle(
            symbol=symbol,
            timestamp=index,
            open=row['Open'],
            high=row['High'],
            low=row['Low'],
            close=row['Close'],
            volume=row['Volume']
        )
        db.add(candle)
    db.commit()

fetch_data("AAPL", "2025-12-01", "2025-12-02")