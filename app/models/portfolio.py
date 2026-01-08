from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    room_id = Column(Integer, ForeignKey("rooms.id"), nullable=False)
    
    initial_balance = Column(Float, default=100000.0)
    current_balance = Column(Float, default=100000.0)  # Cash available

    user = relationship("User")
    room = relationship("Room", back_populates="portfolios")
    positions = relationship("Position", back_populates="portfolio")
