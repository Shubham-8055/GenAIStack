"""
Database initialization — create all tables on startup.
"""
from backend.models.database import Base
from backend.db.engine import engine


async def init_db():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[DB] All tables created / verified.")
