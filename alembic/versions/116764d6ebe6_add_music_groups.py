"""Add music groups

Revision ID: 116764d6ebe6
Revises: 
Create Date: 2025-11-01 00:19:30.314630

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '116764d6ebe6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create music_groups table
    op.create_table(
        'music_groups',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('color', sa.String(length=7), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('ix_music_groups_created_at', 'music_groups', ['created_at'], unique=False)
    
    # Create music_group_members table
    op.create_table(
        'music_group_members',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('group_id', sa.UUID(), nullable=False),
        sa.Column('music_filename', sa.String(length=500), nullable=False),
        sa.Column('order', sa.Integer(), nullable=True),
        sa.Column('added_at', sa.TIMESTAMP(), nullable=False),
        sa.ForeignKeyConstraint(['group_id'], ['music_groups.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('group_id', 'music_filename', name='uq_group_music')
    )
    op.create_index('ix_music_group_members_group_id', 'music_group_members', ['group_id'], unique=False)
    op.create_index('ix_music_group_members_order', 'music_group_members', ['order'], unique=False)
    op.create_index('ix_music_group_members_added_at', 'music_group_members', ['added_at'], unique=False)


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_index('ix_music_group_members_added_at', table_name='music_group_members')
    op.drop_index('ix_music_group_members_order', table_name='music_group_members')
    op.drop_index('ix_music_group_members_group_id', table_name='music_group_members')
    op.drop_table('music_group_members')
    op.drop_index('ix_music_groups_created_at', table_name='music_groups')
    op.drop_table('music_groups')

