"""add_user_priority

Revision ID: 35d082689f34
Revises: a1b2c3d4e5f6
Create Date: 2025-12-26 19:14:49.105929

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '35d082689f34'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add priority column to users table
    # Default value is 50 (middle priority)
    op.add_column('users', sa.Column('priority', sa.Integer(), nullable=False, server_default='50'))
    op.create_index(op.f('ix_users_priority'), 'users', ['priority'], unique=False)


def downgrade() -> None:
    # Remove priority column
    op.drop_index(op.f('ix_users_priority'), table_name='users')
    op.drop_column('users', 'priority')

