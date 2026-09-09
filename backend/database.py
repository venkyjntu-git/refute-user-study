"""
Database engine/session setup.

DATABASE_URL holds the connection string, both locally (backend/.env) and on
Render. Unset, it falls back to a local SQLite file so the app runs with no
configuration at all.

Supabase hands out URLs starting with `postgresql://`; SQLAlchemy would pick
psycopg2 for that, so we rewrite the scheme to psycopg (v3), which is the
driver in requirements.txt.
"""
import os
import re

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

try:  # local dev convenience; not required in production
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./refute_study.db")

# postgres:// and postgresql:// -> postgresql+psycopg:// (psycopg 3)
DATABASE_URL = re.sub(r"^postgres(ql)?://", "postgresql+psycopg://", DATABASE_URL)

if DATABASE_URL.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    engine_kwargs = {}
else:
    # Supabase terminates idle connections; pre_ping + recycle keeps the
    # pooled connections from going stale between study sessions.
    connect_args = {"sslmode": "require"}
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
        "pool_size": 5,
        "max_overflow": 5,
    }

engine = create_engine(DATABASE_URL, connect_args=connect_args, **engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
