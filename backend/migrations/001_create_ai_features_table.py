"""
Create ai_features table for ML feature storage
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '001_create_ai_features'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create ai_features table
    op.create_table(
        'ai_features',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('pcr', sa.Float(), nullable=True),
        sa.Column('gamma_exposure', sa.Float(), nullable=True),
        sa.Column('oi_velocity', sa.Float(), nullable=True),
        sa.Column('volatility', sa.Float(), nullable=True),
        sa.Column('trend_strength', sa.Float(), nullable=True),
        sa.Column('liquidity_score', sa.Float(), nullable=True),
        sa.Column('market_regime', sa.String(length=20), nullable=True),
        sa.Column('feature_vector_json', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_ai_features_symbol_timestamp', 'ai_features', ['symbol', 'timestamp'])
    op.create_index('idx_ai_features_timestamp', 'ai_features', ['timestamp'])

def downgrade():
    op.drop_table('ai_features')
