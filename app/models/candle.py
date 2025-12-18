from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint
from app.db.base import Base

class Candle(Base):
    __tablename__ = "candles"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, index=True, nullable=False)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float, nullable=False) # yfinance volume can be float sometimes, but usually int. Float is safer.

    # Ensure we don't have duplicate candles for the same symbol and time
    __table_args__ = (
        UniqueConstraint('symbol', 'timestamp', name='uix_symbol_timestamp'),
    )
