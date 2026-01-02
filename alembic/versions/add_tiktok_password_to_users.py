"""add_tiktok_password_to_users

Revision ID: add_tiktok_password
Revises: 35d082689f34
Create Date: 2026-01-02 14:40:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_tiktok_password'
down_revision: Union[str, None] = '35d082689f34'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add tiktok_password column to users table
    # This stores the original TikTok account password for posting functionality
    op.add_column('users', sa.Column('tiktok_password', sa.String(255), nullable=True))


def downgrade() -> None:
    # Remove tiktok_password column
    op.drop_column('users', 'tiktok_password')

