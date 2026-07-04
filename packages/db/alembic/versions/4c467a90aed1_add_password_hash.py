"""add_password_hash

Revision ID: 4c467a90aed1
Revises: 74cde41194d4
Create Date: 2026-07-04 20:30:06.896436

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4c467a90aed1'
down_revision: Union[str, Sequence[str], None] = '74cde41194d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("ALTER TABLE users DROP COLUMN password_hash")
