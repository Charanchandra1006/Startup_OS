"""initial_schema

Revision ID: 74cde41194d4
Revises: 
Create Date: 2026-07-04 17:02:18.196300

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import os


# revision identifiers, used by Alembic.
revision: str = '74cde41194d4'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Read the consolidated init.sql file to bootstrap the Neon database
    init_sql_path = os.path.join(os.path.dirname(__file__), "..", "..", "init.sql")
    with open(init_sql_path, "r", encoding="utf-8") as f:
        sql = f.read()
    
    # asyncpg does not support executing multiple commands in a single prepared statement.
    import re
    # Remove single-line comments
    sql_no_comments = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
    # Split by semicolon
    statements = sql_no_comments.split(';')
    for statement in statements:
        if statement.strip():
            op.execute(sa.text(statement))


def downgrade() -> None:
    # MVP: Downgrade drops the schema or we leave it as pass
    pass
