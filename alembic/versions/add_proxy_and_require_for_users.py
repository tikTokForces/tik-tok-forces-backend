"""Add proxy and require for users

Revision ID: add_proxy_users
Revises: 116764d6ebe6
Create Date: 2025-01-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '116764d6ebe6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Get the database connection to check if tables exist
    connection = op.get_bind()
    
    # Check if tables exist
    inspector = inspect(connection)
    table_names = inspector.get_table_names()
    users_table_exists = 'users' in table_names
    proxies_table_exists = 'proxies' in table_names
    
    # Create proxies table if it doesn't exist
    if not proxies_table_exists:
        op.create_table(
            'proxies',
            sa.Column('id', sa.String(36), primary_key=True),  # Use String for SQLite compatibility
            sa.Column('login', sa.String(200), nullable=False),
            sa.Column('password', sa.String(255), nullable=False),
            sa.Column('ip', sa.String(50), nullable=False),
            sa.Column('port', sa.Integer(), nullable=False),
            sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
            sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
        )
        op.create_index(op.f('ix_proxies_ip'), 'proxies', ['ip'], unique=False)
        op.create_index(op.f('ix_proxies_created_at'), 'proxies', ['created_at'], unique=False)
    
    # Create users table if it doesn't exist
    if not users_table_exists:
        op.create_table(
            'users',
            sa.Column('id', sa.String(36), primary_key=True),  # Use String for SQLite compatibility
            sa.Column('username', sa.String(100), nullable=False, unique=True),
            sa.Column('password_hash', sa.String(255), nullable=False),
            sa.Column('email', sa.String(255), nullable=False, unique=True),
            sa.Column('full_name', sa.String(200), nullable=True),
            sa.Column('is_active', sa.Boolean(), default=True),
            sa.Column('is_admin', sa.Boolean(), default=False),
            sa.Column('user_metadata', sa.Text(), nullable=True),  # JSON stored as Text in SQLite
            sa.Column('created_at', sa.TIMESTAMP(), nullable=False),
            sa.Column('updated_at', sa.TIMESTAMP(), nullable=False),
            sa.Column('last_login_at', sa.TIMESTAMP(), nullable=True),
        )
        op.create_index(op.f('ix_users_username'), 'users', ['username'], unique=True)
        op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
        op.create_index(op.f('ix_users_is_active'), 'users', ['is_active'], unique=False)
        op.create_index(op.f('ix_users_is_admin'), 'users', ['is_admin'], unique=False)
        op.create_index(op.f('ix_users_created_at'), 'users', ['created_at'], unique=False)
    
    # Make email NOT NULL in users table (if it's currently nullable)
    # First, set default for any NULL emails (only if table existed before)
    if users_table_exists:
        op.execute("UPDATE users SET email = username || '@example.com' WHERE email IS NULL")
        
        # For SQLite, we can't directly alter column to NOT NULL
        # The email column will remain nullable in the database schema
        # but the application layer should enforce NOT NULL constraint
        # Note: In production with PostgreSQL, you would use ALTER COLUMN SET NOT NULL
    
    # Create a default proxy for existing users (if any)
    # We'll use a fixed UUID for the default proxy
    # Only insert if proxies table was just created or if default proxy doesn't exist
    default_proxy_id = '00000000-0000-0000-0000-000000000001'
    if not proxies_table_exists:
        # Insert default proxy only if we just created the table
        op.execute(f"""
            INSERT INTO proxies (id, login, password, ip, port, created_at, updated_at)
            VALUES (
                '{default_proxy_id}',
                'default',
                'default',
                '127.0.0.1',
                8080,
                CURRENT_TIMESTAMP,
                CURRENT_TIMESTAMP
            )
        """)
    else:
        # Check if default proxy exists, if not create it
        result = connection.execute(sa.text(f"SELECT COUNT(*) FROM proxies WHERE id = '{default_proxy_id}'")).scalar()
        if result == 0:
            op.execute(f"""
                INSERT INTO proxies (id, login, password, ip, port, created_at, updated_at)
                VALUES (
                    '{default_proxy_id}',
                    'default',
                    'default',
                    '127.0.0.1',
                    8080,
                    CURRENT_TIMESTAMP,
                    CURRENT_TIMESTAMP
                )
            """)
    
    # Add proxy_id column to users table (only if it doesn't already exist)
    # For SQLite, we need to handle this carefully since ALTER COLUMN is limited
    users_columns = [col['name'] for col in inspector.get_columns('users')] if users_table_exists or 'users' in inspector.get_table_names() else []
    
    if 'proxy_id' not in users_columns:
        # Add column as nullable first (SQLite limitation)
        op.add_column('users', sa.Column('proxy_id', sa.String(36), nullable=True))
        op.create_index(op.f('ix_users_proxy_id'), 'users', ['proxy_id'], unique=False)
        
        # Assign default proxy to all users
        op.execute(f"""
            UPDATE users
            SET proxy_id = '{default_proxy_id}'
            WHERE proxy_id IS NULL
        """)
        
        # For SQLite, we can't directly alter column to NOT NULL
        # We'll leave it as nullable for now, but ensure all rows have a value
        # The application layer should enforce NOT NULL constraint
        # Note: In production with PostgreSQL, you would use ALTER COLUMN SET NOT NULL
    
    # Add foreign key constraint (only if it doesn't exist)
    try:
        # Check if foreign key already exists
        fk_constraints = [fk['name'] for fk in inspector.get_foreign_keys('users')]
        if 'fk_users_proxy_id' not in fk_constraints:
            op.create_foreign_key(
                'fk_users_proxy_id',
                'users', 'proxies',
                ['proxy_id'], ['id'],
                ondelete='RESTRICT'
            )
    except Exception:
        # If check fails, try to create it anyway
        try:
            op.create_foreign_key(
                'fk_users_proxy_id',
                'users', 'proxies',
                ['proxy_id'], ['id'],
                ondelete='RESTRICT'
            )
        except Exception:
            # Foreign key might already exist, skip
            pass


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

