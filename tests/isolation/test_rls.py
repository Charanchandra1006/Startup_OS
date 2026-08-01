"""
Chief AI Startup OS — Row Level Security Enforcement Tests
Implements: STARTUP_OS_MASTER_BUILD_PLAN Part 10.3

Tests that RLS policies on goal_events, tool_connections, and existing
tables prevent cross-tenant data access.

Requires: PostgreSQL with init.sql applied and RLS policies active.
Skips gracefully if no DATABASE_URL is set (local dev without DB).
"""

import os
import sys
import uuid
import pytest
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../packages/shared-types/python")))

TENANT_A = str(uuid.uuid4())
TENANT_B = str(uuid.uuid4())
USER_A = str(uuid.uuid4())
USER_B = str(uuid.uuid4())


@pytest.fixture(scope="module")
def db_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set — skipping RLS tests")
    return url.replace("postgresql+asyncpg://", "postgresql://").split("?")[0]


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def db_pool(db_url):
    import asyncpg
    pool = await asyncpg.create_pool(db_url, ssl="require")
    yield pool
    await pool.close()


@pytest.fixture(scope="module")
async def seed_data(db_pool):
    """Seed two tenants with separate data."""
    async with db_pool.acquire() as conn:
        # Create tenants
        await conn.execute(
            "INSERT INTO tenants (id, name) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            uuid.UUID(TENANT_A), "RLS Test Tenant A",
        )
        await conn.execute(
            "INSERT INTO tenants (id, name) VALUES ($1, $2) ON CONFLICT DO NOTHING",
            uuid.UUID(TENANT_B), "RLS Test Tenant B",
        )
        # Create users
        await conn.execute(
            "INSERT INTO users (id, tenant_id, email, name, role) VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
            uuid.UUID(USER_A), uuid.UUID(TENANT_A), f"a@test.com", "User A", "founder",
        )
        await conn.execute(
            "INSERT INTO users (id, tenant_id, email, name, role) VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
            uuid.UUID(USER_B), uuid.UUID(TENANT_B), f"b@test.com", "User B", "founder",
        )
        
        # Create goal_events for each tenant
        goal_a = uuid.uuid4()
        goal_b = uuid.uuid4()
        
        await conn.execute(
            "INSERT INTO goals (id, tenant_id, submitted_by_user_id, raw_text, status) VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
            goal_a, uuid.UUID(TENANT_A), uuid.UUID(USER_A), "Test goal A", "received",
        )
        await conn.execute(
            "INSERT INTO goals (id, tenant_id, submitted_by_user_id, raw_text, status) VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING",
            goal_b, uuid.UUID(TENANT_B), uuid.UUID(USER_B), "Test goal B", "received",
        )
        
        await conn.execute(
            "INSERT INTO goal_events (goal_id, tenant_id, state) VALUES ($1, $2, $3)",
            goal_a, uuid.UUID(TENANT_A), "CLASSIFYING",
        )
        await conn.execute(
            "INSERT INTO goal_events (goal_id, tenant_id, state) VALUES ($1, $2, $3)",
            goal_b, uuid.UUID(TENANT_B), "DISPATCHING",
        )
        
        yield {"goal_a": goal_a, "goal_b": goal_b}
        
        # Cleanup
        await conn.execute("DELETE FROM goal_events WHERE tenant_id IN ($1, $2)", uuid.UUID(TENANT_A), uuid.UUID(TENANT_B))
        await conn.execute("DELETE FROM goals WHERE tenant_id IN ($1, $2)", uuid.UUID(TENANT_A), uuid.UUID(TENANT_B))
        await conn.execute("DELETE FROM users WHERE tenant_id IN ($1, $2)", uuid.UUID(TENANT_A), uuid.UUID(TENANT_B))
        await conn.execute("DELETE FROM tenants WHERE id IN ($1, $2)", uuid.UUID(TENANT_A), uuid.UUID(TENANT_B))


@pytest.mark.asyncio
class TestGoalEventsRLS:
    """Test RLS on the goal_events table."""

    async def test_tenant_a_cannot_see_tenant_b_events(self, db_pool, seed_data):
        """Tenant A should only see their own goal_events."""
        async with db_pool.acquire() as conn:
            # Set the session tenant to A
            await conn.execute(f"SET app.current_tenant_id = '{TENANT_A}'")
            rows = await conn.fetch("SELECT * FROM goal_events")
            
            for row in rows:
                assert str(row["tenant_id"]) == TENANT_A, \
                    f"Tenant A saw tenant_id={row['tenant_id']}, expected {TENANT_A}"

    async def test_tenant_b_cannot_see_tenant_a_events(self, db_pool, seed_data):
        """Tenant B should only see their own goal_events."""
        async with db_pool.acquire() as conn:
            await conn.execute(f"SET app.current_tenant_id = '{TENANT_B}'")
            rows = await conn.fetch("SELECT * FROM goal_events")
            
            for row in rows:
                assert str(row["tenant_id"]) == TENANT_B, \
                    f"Tenant B saw tenant_id={row['tenant_id']}, expected {TENANT_B}"

    async def test_wrong_tenant_gets_zero_rows(self, db_pool, seed_data):
        """A random tenant should see zero goal_events."""
        random_tenant = str(uuid.uuid4())
        async with db_pool.acquire() as conn:
            await conn.execute(f"SET app.current_tenant_id = '{random_tenant}'")
            rows = await conn.fetch("SELECT * FROM goal_events")
            assert len(rows) == 0, \
                f"Random tenant saw {len(rows)} rows, expected 0"


@pytest.mark.asyncio
class TestGoalsRLS:
    """Test RLS on the goals table."""

    async def test_cross_tenant_goal_invisible(self, db_pool, seed_data):
        """Tenant A should not see Tenant B's goals."""
        async with db_pool.acquire() as conn:
            await conn.execute(f"SET app.current_tenant_id = '{TENANT_A}'")
            rows = await conn.fetch("SELECT * FROM goals")
            
            for row in rows:
                assert str(row["tenant_id"]) == TENANT_A
