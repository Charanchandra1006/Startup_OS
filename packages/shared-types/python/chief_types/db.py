"""
Chief AI Startup OS — Database Connection Layer
Implements: DDD §1 (Data Classification) & RLS injection

Provides async database session management using SQLAlchemy and asyncpg.
Configured for Neon PostgreSQL cloud environment.
CRITICAL: Every query MUST be wrapped in a tenant context so that RLS policies apply.
"""

import contextlib
import logging
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger("chief.db")

# Base model for all SQLAlchemy entities
Base = declarative_base()


class DatabaseManager:
    """Manages connections to a PostgreSQL database (optimized for Neon)."""

    def __init__(self, name: str):
        """
        Initialize connection manager. 
        For MVP, all managers use the single Neon DATABASE_URL, but keeping
        separate instances allows future scaling to multiple databases.
        """
        self.name = name
        self.engine: AsyncEngine | None = None
        self.session_factory: sessionmaker | None = None

    def connect(self) -> None:
        """Initialize the SQLAlchemy async engine for Neon PostgreSQL."""
        # For MVP, all connect to the same Neon instance
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            raise ValueError("DATABASE_URL environment variable is missing. Cannot connect to Neon PostgreSQL.")
            
        # Ensure we are using asyncpg
        if db_url.startswith("postgres://") or db_url.startswith("postgresql://"):
            db_url = db_url.replace("postgres://", "postgresql+asyncpg://", 1)
            db_url = db_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            
        # asyncpg does not support sslmode in the connection string
        db_url = db_url.replace("?sslmode=require", "?ssl=require")
        db_url = db_url.replace("&sslmode=require", "&ssl=require")
        db_url = db_url.replace("?channel_binding=require", "")
        db_url = db_url.replace("&channel_binding=require", "")
        if db_url.endswith("?"): db_url = db_url[:-1]

        self.engine = create_async_engine(
            db_url,
            pool_size=10,
            max_overflow=20,
            pool_recycle=300,  # Recycle connections every 5 mins (good for serverless DBs like Neon)
            pool_pre_ping=True, # Automatic reconnect on dropped connections
            connect_args={
                "ssl": "require"
            },
            echo=False,
        )
        
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info(f"Initialized Neon DatabaseManager for {self.name} store.")

    async def disconnect(self) -> None:
        """Close the database engine."""
        if self.engine:
            await self.engine.dispose()
            logger.info(f"Closed DatabaseManager for {self.name} store.")

    async def check_health(self) -> bool:
        """Ping the database to verify connectivity."""
        if not self.engine:
            return False
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as e:
            logger.error(f"Health check failed for {self.name}: {e}")
            return False

    @contextlib.asynccontextmanager
    async def tenant_session(self, tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
        """
        Yields an AsyncSession where the current tenant is injected into the Postgres context.
        This is CRITICAL for Row-Level Security (RLS) enforcement (DDD §1).
        """
        if not self.session_factory:
            raise RuntimeError(f"DatabaseManager for {self.name} is not connected.")

        async with self.session_factory() as session:
            try:
                # Inject tenant_id into the postgres transaction configuration
                # This makes current_setting('app.current_tenant_id') work in RLS policies
                await session.execute(
                    text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
                    {"tenant_id": tenant_id}
                )
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Database session error (tenant {tenant_id}): {e}")
                raise
            finally:
                await session.close()


# Global instances for the distinct data stores.
# For the MVP, these all route to the same Neon database, fulfilling Req 12
# (compatible with future migration to multiple DBs if required).
operational_db = DatabaseManager("OPERATIONAL")
financial_db = DatabaseManager("FINANCIAL")
documents_db = DatabaseManager("DOCUMENTS")
