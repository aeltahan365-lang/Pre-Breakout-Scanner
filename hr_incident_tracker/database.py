import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

from . import config

os.makedirs(os.path.join(os.path.dirname(__file__), "data"), exist_ok=True)

connect_args = {"check_same_thread": False} if config.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(config.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
