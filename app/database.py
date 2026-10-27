import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def database_url() -> str:
    value = os.getenv("DATABASE_URL", "sqlite:///./tracerag.db")
    if value.startswith("mysql://"):
        value = value.replace("mysql://", "mysql+pymysql://", 1)
    return value


DATABASE_URL = database_url()
CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {
    "connect_timeout": 8,
    "read_timeout": 15,
    "write_timeout": 15,
}
engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=300, connect_args=CONNECT_ARGS)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

