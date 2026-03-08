"""merge migrations

Revision ID: de1284eb1c42
Revises: 7a49316b4b04, add_ai_signal_logs_table_v2, add_performance_indexes, add_performance_indexes_fixed, create_ai_signal_logs
Create Date: 2026-03-08 18:51:40.122252

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'de1284eb1c42'
down_revision: Union[str, Sequence[str], None] = ('7a49316b4b04', 'add_ai_signal_logs_table_v2', 'add_performance_indexes', 'add_performance_indexes_fixed', 'create_ai_signal_logs')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass
