"""Add proxy and require for users

Revision ID: add_proxy_users
Revises: 116764d6ebe6
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '116764d6ebe6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create proxies table
    op.create_table(
        'proxies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('login', sa.String(200), nullable=False),
        sa.Column('password', sa.String(255), nullable=False),
        sa.Column('ip', sa.String(50), nullable=False),
        sa.Column('port', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
    )
    op.create_index(op.f('ix_proxies_ip'), 'proxies', ['ip'], unique=False)
    op.create_index(op.f('ix_proxies_created_at'), 'proxies', ['created_at'], unique=False)
    
    # Make email NOT NULL in users table (if it's currently nullable)
    # First, set default for any NULL emails
    op.execute("UPDATE users SET email = username || '@example.com' WHERE email IS NULL")
    
    # Make email NOT NULL
    op.alter_column('users', 'email',
                    existing_type=sa.String(255),
                    nullable=False)
    
    # Add proxy_id column to users table
    op.add_column('users', sa.Column('proxy_id', postgresql.UUID(as_uuid=True), nullable=True))
    op.create_index(op.f('ix_users_proxy_id'), 'users', ['proxy_id'], unique=False)
    
    # Create a default proxy for existing users (if any)
    # We'll use a fixed UUID for the default proxy
    default_proxy_id = '00000000-0000-0000-0000-000000000001'
    op.execute(f"""
        INSERT INTO proxies (id, login, password, ip, port, created_at, updated_at)
        VALUES (
            '{default_proxy_id}'::uuid,
            'default',
            'default',
            '127.0.0.1',
            8080,
            CURRENT_TIMESTAMP,
            CURRENT_TIMESTAMP
        )
    """)
    
    # Assign default proxy to existing users
    op.execute(f"""
        UPDATE users
        SET proxy_id = '{default_proxy_id}'::uuid
        WHERE proxy_id IS NULL
    """)
    
    # Now make proxy_id NOT NULL
    op.alter_column('users', 'proxy_id',
                    existing_type=postgresql.UUID(as_uuid=True),
                    nullable=False)
    
    # Add foreign key constraint
    op.create_foreign_key(
        'fk_users_proxy_id',
        'users', 'proxies',
        ['proxy_id'], ['id'],
        ondelete='RESTRICT'
    )


def downgrade() -> None:
    # Remove foreign key constraint
    op.drop_constraint('fk_users_proxy_id', 'users', type_='foreignkey')
    
    # Remove proxy_id column
    op.drop_index(op.f('ix_users_proxy_id'), table_name='users')
    op.drop_column('users', 'proxy_id')
    
    # Make email nullable again
    op.alter_column('users', 'email',
                    existing_type=sa.String(255),
                    nullable=True)
    
    # Drop proxies table
    op.drop_index(op.f('ix_proxies_created_at'), table_name='proxies')
    op.drop_index(op.f('ix_proxies_ip'), table_name='proxies')
    op.drop_table('proxies')

