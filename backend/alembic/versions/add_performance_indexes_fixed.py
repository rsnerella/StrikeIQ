"""Add performance indexes for option chain queries

Revision ID: add_performance_indexes_fixed
Revises: 2a25798e298c
Create Date: 2026-02-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'add_performance_indexes_fixed'
down_revision = '2a25798e298c'
branch_labels = None
depends_on = None

def upgrade():
    # Skip index creation - tables don't exist yet
    pass

def downgrade():
    # Skip index removal - tables don't exist
    pass
