"""add_name_to_tracked_meal

Revision ID: 7fdcc454e056
Revises: e1c2d8d5c1a8
Create Date: 2026-02-24 06:29:46.441129

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7fdcc454e056'
down_revision: Union[str, None] = 'e1c2d8d5c1a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('tracked_meals', sa.Column('name', sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('tracked_meals') as batch_op:
        batch_op.drop_column('name')
