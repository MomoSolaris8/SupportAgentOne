import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

load_dotenv()


def get_database_url() -> str:
    url = os.environ["DATABASE_URL"]
    url = url.replace("postgres://", "postgresql://", 1)
    return url.replace("postgres://", "postgresql+psycopg://", 1)


engine = create_engine(
    get_database_url(),
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    connect_args={
        "prepare_threshold": None,
        "connect_timeout": int(os.environ.get("DATABASE_CONNECT_TIMEOUT_SECONDS", "5")),
    },
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
