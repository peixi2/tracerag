import os
from urllib.parse import quote_plus, urlsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


def database_url() -> str:
    value = os.getenv("DATABASE_URL")
    if not value:
        jdbc_url = os.getenv("DB_URL", "")
        if jdbc_url.startswith("jdbc:mysql://"):
            parsed = urlsplit(jdbc_url.removeprefix("jdbc:"))
            username = quote_plus(os.getenv("DB_USERNAME", ""))
            password = quote_plus(os.getenv("DB_PASSWORD", ""))
            port = f":{parsed.port}" if parsed.port else ""
            database = os.getenv("DB_NAME", "tracerag")
            value = f"mysql+pymysql://{username}:{password}@{parsed.hostname}{port}/{database}?charset=utf8mb4"
        else:
            value = "sqlite:///./tracerag.db"
    if value.startswith("mysql://"):
        value = value.replace("mysql://", "mysql+pymysql://", 1)
    return value


DATABASE_URL = database_url()
CONNECT_ARGS = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {
    "connect_timeout": 8,
    "read_timeout": 15,
    "write_timeout": 15,
    "ssl": {"check_hostname": True} if os.getenv("DB_URL", "").startswith("jdbc:mysql://") else None,
}
CONNECT_ARGS = {key: value for key, value in CONNECT_ARGS.items() if value is not None}
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

