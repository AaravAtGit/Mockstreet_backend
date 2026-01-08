from sqlalchemy.orm import Session
from sqlalchemy import create_engine

from app.db.base import Base # noqa
from app.db.session import engine # noqa
from app.models.user import User # noqa
from app.models.candle import Candle # noqa
from app.models.room import Room # noqa
from app.models.portfolio import Portfolio # noqa
from app.models.position import Position # noqa

def init_db(db: Session):
    # Base.metadata.drop_all(bind=engine) # Use with caution! Clears all data.
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    from app.core.config import settings
    # Ensure the database directory exists
    import os
    os.makedirs(os.path.dirname(settings.DATABASE_URL.replace("sqlite:///", "")), exist_ok=True)
    init_db(Session(engine))
    print("Database initialized and tables created.")
