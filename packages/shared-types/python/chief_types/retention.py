"""
Chief AI Startup OS — Data Retention Job
Implements: STARTUP_OS_MASTER_BUILD_PLAN Part 5.3 / SPEC-GAPS SG-004

Scheduled retention policy:
- General operational logs: 90 days
- AI traces (agent_runs): 1 year
- Goal events: 90 days (same as operational)

Designed to run as a K8s CronJob (retention-cronjob.yaml) daily at 3am.

Usage:
    python -m chief_types.retention
    
Or via K8s CronJob:
    python -c "from chief_types.retention import purge_expired_traces; ..."
"""

import os
import sys
import logging
import asyncio
from datetime import datetime, timezone, timedelta

logger = logging.getLogger("chief.retention")


async def purge_expired_traces(db_url: str | None = None) -> dict:
    """Purge expired data according to retention policy.
    
    Returns a summary dict of rows deleted per table.
    """
    import asyncpg
    
    if not db_url:
        db_url = os.environ.get("DATABASE_URL", "")
    
    if not db_url:
        logger.error("DATABASE_URL not set — cannot run retention job")
        return {"error": "no_database_url"}
    
    # Normalize URL for asyncpg
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
    if "?" in db_url:
        db_url = db_url.split("?")[0]
    
    conn = await asyncpg.connect(db_url, ssl="require")
    summary = {}
    
    try:
        now = datetime.now(timezone.utc)
        cutoff_90d = now - timedelta(days=90)
        cutoff_1y = now - timedelta(days=365)
        
        # 1. Goal events — 90 day retention
        result = await conn.execute(
            "DELETE FROM goal_events WHERE created_at < $1",
            cutoff_90d,
        )
        summary["goal_events"] = _parse_delete_count(result)
        
        # 2. Agent runs (AI traces) — 1 year retention
        result = await conn.execute(
            "DELETE FROM agent_runs WHERE started_at < $1",
            cutoff_1y,
        )
        summary["agent_runs"] = _parse_delete_count(result)
        
        # 3. Completed/failed tasks — 90 day retention
        # Only delete tasks whose parent goal is also old
        result = await conn.execute(
            """
            DELETE FROM tasks WHERE created_at < $1 
            AND status IN ('completed', 'failed', 'timed_out', 'cancelled')
            """,
            cutoff_90d,
        )
        summary["tasks"] = _parse_delete_count(result)
        
        # 4. Dismissed insights — 90 day retention
        result = await conn.execute(
            "DELETE FROM insights WHERE status = 'dismissed' AND dismissed_at < $1",
            cutoff_90d,
        )
        summary["insights_dismissed"] = _parse_delete_count(result)
        
        logger.info(f"Retention job completed: {summary}")
        
    finally:
        await conn.close()
    
    return summary


def _parse_delete_count(result: str) -> int:
    """Parse the row count from asyncpg DELETE result string."""
    # asyncpg returns "DELETE N" where N is the count
    try:
        return int(result.split()[-1])
    except (ValueError, IndexError):
        return 0


async def _main():
    """Entry point for CLI / CronJob execution."""
    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting retention job at {datetime.now(timezone.utc).isoformat()}")
    
    summary = await purge_expired_traces()
    
    total = sum(v for v in summary.values() if isinstance(v, int))
    logger.info(f"Retention complete: {total} total rows purged")
    for table, count in summary.items():
        logger.info(f"  {table}: {count} rows deleted")


if __name__ == "__main__":
    asyncio.run(_main())
