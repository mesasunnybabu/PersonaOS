# backend/database.py
#
# PURPOSE: This file handles ONE thing — the connection to SQLite.
# Every other file that needs the database imports from here.
# This is the "single source of truth" for database configuration.

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# ── Database URL ──────────────────────────────────────────────────────────────
#
# SQLAlchemy uses a "connection string" to know what database to connect to.
# Format: "dialect+driver://path/to/file"
#
# "sqlite:///" means: use SQLite, and the file path follows
# "./personaos.db" means: create/open the file in the current directory (backend/)
#
# When you run uvicorn from the backend/ folder, this file appears as:
# personaos/backend/personaos.db

DATABASE_URL = "sqlite:///./personaos.db"

# ── Engine ────────────────────────────────────────────────────────────────────
#
# The "engine" is the core connection to the database.
# Think of it as the database "driver" — it knows how to speak SQLite.
#
# connect_args={"check_same_thread": False} is SQLite-specific.
# SQLite by default only allows one thread to use it.
# FastAPI uses multiple threads, so we disable that restriction.

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# ── Session Factory ───────────────────────────────────────────────────────────
#
# A "session" is like a temporary workspace for database operations.
# You open a session, do some reads/writes, then close it.
# SessionLocal is a "factory" — calling SessionLocal() creates a new session.
#
# autocommit=False → we manually control when to save (commit) changes
# autoflush=False  → don't auto-send SQL to the DB before commit

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# ── Base Class ────────────────────────────────────────────────────────────────
#
# All SQLAlchemy models (table definitions) inherit from Base.
# This lets SQLAlchemy track them and create the corresponding tables.

Base = declarative_base()

# ── Dependency: get_db ────────────────────────────────────────────────────────
#
# This is a FastAPI "dependency" — a reusable function that FastAPI
# calls automatically before each route that needs a database session.
#
# The "yield" makes it a generator:
#   1. Code before yield runs BEFORE the route (opens session)
#   2. The route runs
#   3. Code after yield runs AFTER the route (closes session)
#
# This guarantees the session is always closed, even if an error occurs.

def get_db():
    db = SessionLocal()
    try:
        yield db          # Hand the session to the route function
    finally:
        db.close()        # Always close, no matter what