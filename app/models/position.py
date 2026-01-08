from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base

class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    
    side = Column(String, nullable=False)  # LONG / SHORT
    quantity = Column(Float, nullable=False)
    leverage = Column(Integer, default=1)
    
    entry_price = Column(Float, nullable=False)
    entry_time = Column(DateTime(timezone=True), server_default=func.now())
    
    exit_price = Column(Float, nullable=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    
    is_open = Column(Boolean, default=True)
    pnl = Column(Float, nullable=True)  # Realized PnL when closed

    portfolio = relationship("Portfolio", back_populates="positions")
