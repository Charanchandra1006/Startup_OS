"""
Chief AI Startup OS — Database Connection Layer
Implements: DDD §1 (Data Classification) & RLS injection

Provides async database session management using SQLAlchemy and asyncpg.
CRITICAL: Every query MUST be wrapped in a tenant context so that RLS policies apply.
"""

import contextlib
import logging
import os
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

logger = logging.getLogger("chief.db")


class DatabaseManager:
    """Manages connections to a specific PostgreSQL database."""

    def __init__(self, db_type: str):
        """
        Initialize connection to one of the 3 separated databases.
        db_type must be 'OPERATIONAL', 'FINANCIAL', or 'DOCUMENTS'.
        """
        self.db_type = db_type.upper()
        self.engine: AsyncEngine | None = None
        self.session_factory: sessionmaker | None = None

    def connect(self) -> None:
        """Initialize the SQLAlchemy async engine."""
        host = os.environ.get(f"{self.db_type}_DB_HOST", "localhost")
        port = os.environ.get(f"{self.db_type}_DB_PORT", "5432")
        db_name = os.environ.get(f"{self.db_type}_DB_NAME", f"chief_{self.db_type.lower()}")
        user = os.environ.get(f"{self.db_type}_DB_USER", "postgres")
        password = os.environ.get(f"{self.db_type}_DB_PASSWORD", "")

        # Use asyncpg driver for asyncio compatibility
        db_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db_name}"
        
        self.engine = create_async_engine(
            db_url,
            pool_size=20,
            max_overflow=10,
            pool_recycle=1800,
            echo=False,  # Set to True for SQL debugging
        )
        
        self.session_factory = sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        logger.info(f"Initialized DatabaseManager for {self.db_type} store.")

    async def disconnect(self) -> None:
        """Close the database engine."""
        if self.engine:
            await self.engine.dispose()
            logger.info(f"Closed DatabaseManager for {self.db_type} store.")

    @contextlib.asynccontextmanager
    async def tenant_session(self, tenant_id: str) -> AsyncGenerator[AsyncSession, None]:
        """
        Yields an AsyncSession where the current tenant is injected into the Postgres context.
        This is CRITICAL for Row-Level Security (RLS) enforcement (DDD §1).
        """
        if not self.session_factory:
            raise RuntimeError(f"DatabaseManager for {self.db_type} is not connected.")

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


# Global instances for the 3 distinct data stores
operational_db = DatabaseManager("OPERATIONAL")
financial_db = DatabaseManager("FINANCIAL")
documents_db = DatabaseManager("DOCUMENTS")
