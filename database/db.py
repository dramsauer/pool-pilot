from pathlib import Path
from typing import Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from database.models import Base


DB_PATH = Path(__file__).parent.parent / "data" / "pool.db"


def get_engine(db_path: Optional[str] = None):
    if db_path is None:
        DB_PATH.parent.mkdir(exist_ok=True)
        db_path = str(DB_PATH)
    return create_engine(f"sqlite:///{db_path}")


def init_db(engine=None):
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)


def get_session(engine=None) -> Session:
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine)()
