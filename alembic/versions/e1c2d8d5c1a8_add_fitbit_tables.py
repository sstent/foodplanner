"""add fitbit tables

Revision ID: e1c2d8d5c1a8
Revises: 4522e2de4143
Create Date: 2026-01-12 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e1c2d8d5c1a8'
down_revision: Union[str, None] = '31fdce040eea'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create fitbit_config table
    op.create_table('fitbit_config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_id', sa.String(), nullable=True),
        sa.Column('client_secret', sa.String(), nullable=True),
        sa.Column('redirect_uri', sa.String(), nullable=True),
        sa.Column('access_token', sa.String(), nullable=True),
        sa.Column('refresh_token', sa.String(), nullable=True),
        sa.Column('expires_at', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_fitbit_config_id'), 'fitbit_config', ['id'], unique=False)

    # Create weight_logs table
    op.create_table('weight_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('source', sa.String(), nullable=True),
        sa.Column('fitbit_log_id', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_weight_logs_date'), 'weight_logs', ['date'], unique=False)
    op.create_index(op.f('ix_weight_logs_fitbit_log_id'), 'weight_logs', ['fitbit_log_id'], unique=True)
    op.create_index(op.f('ix_weight_logs_id'), 'weight_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_weight_logs_id'), table_name='weight_logs')
    op.drop_index(op.f('ix_weight_logs_fitbit_log_id'), table_name='weight_logs')
    op.drop_index(op.f('ix_weight_logs_date'), table_name='weight_logs')
    op.drop_table('weight_logs')
    op.drop_index(op.f('ix_fitbit_config_id'), table_name='fitbit_config')
    op.drop_table('fitbit_config')
