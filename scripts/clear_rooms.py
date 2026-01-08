import sys
import os

# Add the parent directory to sys.path to import app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.models.room import Room
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.models.user import User

def clear_rooms():
    db = SessionLocal()
    try:
        print("Clearing positions...")
        db.query(Position).delete()
        
        print("Clearing portfolios...")
        db.query(Portfolio).delete()
        
        print("Clearing rooms...")
        db.query(Room).delete()
        
        db.commit()
        print("Successfully cleared all rooms and related data.")
    except Exception as e:
        print(f"Error clearing tables: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    clear_rooms()
