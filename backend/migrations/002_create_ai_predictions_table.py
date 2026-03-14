"""
Create ai_predictions table for ML prediction logging
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '002_create_ai_predictions'
down_revision = '001_create_ai_features'
branch_labels = None
depends_on = None

def upgrade():
    # Create ai_predictions table
    op.create_table(
        'ai_predictions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('features', postgresql.JSONB(), nullable=True),
        sa.Column('buy_probability', sa.Float(), nullable=True),
        sa.Column('sell_probability', sa.Float(), nullable=True),
        sa.Column('strategy', sa.String(length=50), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('model_version', sa.String(length=20), nullable=True),
        sa.Column('signal_type', sa.String(length=20), nullable=True),
        sa.Column('prediction_successful', sa.Boolean(), nullable=True),
        sa.Column('feature_importance', postgresql.JSONB(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes for performance
    op.create_index('idx_ai_predictions_symbol_timestamp', 'ai_predictions', ['symbol', 'timestamp'])
    op.create_index('idx_ai_predictions_timestamp', 'ai_predictions', ['timestamp'])
    op.create_index('idx_ai_predictions_confidence', 'ai_predictions', ['confidence_score'])

def downgrade():
    op.drop_table('ai_predictions')
