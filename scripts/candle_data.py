import yfinance as yf
from app.db.session import SessionLocal
from app.models.candle import Candle

db = SessionLocal()

TICKERS = [
    # Crypto
    "BTC-USD", "ETH-USD", "SOL-USD", "DOGE-USD",
    # Stocks (US)
    "AAPL", "TSLA", "NVDA", "MSFT", "AMD", "GOOGL", "AMZN",
    # Forex
    "EURUSD=X", "GBPUSD=X", "USDJPY=X",
    # Indices / Nifty (India)
    "^NSEI", "^BSESN",
    # Indian Stocks
    "RELIANCE.NS", "TCS.NS", "INFY.NS"
]

def fetch_data():
    print(f"Fetching data for {len(TICKERS)} tickers...")
    
    for symbol in TICKERS:
        print(f"Downloading {symbol}...")
        try:
            # Fetch last 5 days of 1m data (maximum available for 1m interval usually)
            data = yf.download(symbol, period="5d", interval="1m", progress=False)
            
            if data.empty:
                print(f"No data found for {symbol}")
                continue
            
            # Get existing timestamps to avoid duplicates
            existing_timestamps = set(
                t[0] for t in db.query(Candle.timestamp)
                .filter(Candle.symbol == symbol)
                .all()
            )
            
            new_candles = []
            for index, row in data.iterrows():
                # Timestamp is the index
                ts = index.to_pydatetime() if hasattr(index, 'to_pydatetime') else index
                
                # Check if already exists
                if ts in existing_timestamps:
                    continue
                
                # Check for NaN values
                if row.isnull().values.any():
                    continue

                candle = Candle(
                    symbol=symbol,
                    timestamp=ts,
                    open=float(row['Open']),
                    high=float(row['High']),
                    low=float(row['Low']),
                    close=float(row['Close']),
                    volume=float(row['Volume'])
                )
                new_candles.append(candle)
            
            if new_candles:
                db.bulk_save_objects(new_candles)
                db.commit()
                print(f"Saved {len(new_candles)} new candles for {symbol}")
            else:
                print(f"No new candles for {symbol}")
            
        except Exception as e:
            print(f"Failed to fetch/save {symbol}: {e}")
            db.rollback()

if __name__ == "__main__":
    fetch_data()