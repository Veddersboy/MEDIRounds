"""better-auth-models

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-31 14:42:10.425811
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '0002'
down_revision: Union[str, Sequence[str], None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Postgres auto-generated these names for the unnamed 0001 foreign keys; reuse them for the new ones.
FK_NAME = {
    "chat_sessions": "chat_sessions_user_id_fkey",
    "user_settings": "user_settings_user_id_fkey",
}
# SQLite keeps no name for the 0001 foreign keys, so batch mode names them with this convention.
SQLITE_FK_NAMING = {"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"}


def repoint_user_fk(table, old_target, new_target, old_type, new_type):
    """Point table.user_id at a different users table. Batch mode lets this run on SQLite too."""
    is_sqlite = op.get_bind().dialect.name == "sqlite"
    # On SQLite, the users foreign key always goes by the convention name, whether 0001 or a downgrade created it.
    old_name = f"fk_{table}_user_id_users" if is_sqlite and old_target == "users" else FK_NAME[table]
    new_name = f"fk_{table}_user_id_users" if is_sqlite and new_target == "users" else FK_NAME[table]
    with op.batch_alter_table(table, naming_convention=SQLITE_FK_NAMING if is_sqlite else None) as batch:
        batch.drop_constraint(old_name, type_="foreignkey")
        batch.alter_column("user_id", existing_type=old_type, type_=new_type, existing_nullable=False)
        batch.create_foreign_key(new_name, new_target, ["user_id"], ["id"], ondelete="CASCADE")


def upgrade() -> None:
    op.create_table('user',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('email', sa.Text(), nullable=False),
    sa.Column('emailVerified', sa.Boolean(), nullable=False),
    sa.Column('image', sa.Text(), nullable=True),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email')
    )
    op.create_table('verification',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('identifier', sa.Text(), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('expiresAt', sa.DateTime(timezone=True), nullable=False),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('verification_identifier_idx', 'verification', ['identifier'], unique=False)
    op.create_table('account',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('accountId', sa.Text(), nullable=False),
    sa.Column('providerId', sa.Text(), nullable=False),
    sa.Column('userId', sa.Text(), nullable=False),
    sa.Column('accessToken', sa.Text(), nullable=True),
    sa.Column('refreshToken', sa.Text(), nullable=True),
    sa.Column('idToken', sa.Text(), nullable=True),
    sa.Column('accessTokenExpiresAt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('refreshTokenExpiresAt', sa.DateTime(timezone=True), nullable=True),
    sa.Column('scope', sa.Text(), nullable=True),
    sa.Column('password', sa.Text(), nullable=True),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['userId'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('account_userId_idx', 'account', ['userId'], unique=False)
    op.create_table('session',
    sa.Column('id', sa.Text(), nullable=False),
    sa.Column('expiresAt', sa.DateTime(timezone=True), nullable=False),
    sa.Column('token', sa.Text(), nullable=False),
    sa.Column('createdAt', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
    sa.Column('updatedAt', sa.DateTime(timezone=True), nullable=False),
    sa.Column('ipAddress', sa.Text(), nullable=True),
    sa.Column('userAgent', sa.Text(), nullable=True),
    sa.Column('userId', sa.Text(), nullable=False),
    sa.ForeignKeyConstraint(['userId'], ['user.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('token')
    )
    op.create_index('session_userId_idx', 'session', ['userId'], unique=False)

    repoint_user_fk("chat_sessions", "users", "user", sa.String(length=36), sa.Text())
    repoint_user_fk("user_settings", "users", "user", sa.String(length=36), sa.Text())

    # Drop last: nothing may still reference users.id.
    op.drop_table('users')


def downgrade() -> None:
    # Deletes every Better Auth account.
    op.create_table('users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )

    repoint_user_fk("user_settings", "user", "users", sa.Text(), sa.String(length=36))
    repoint_user_fk("chat_sessions", "user", "users", sa.Text(), sa.String(length=36))

    op.drop_index('session_userId_idx', table_name='session')
    op.drop_table('session')
    op.drop_index('account_userId_idx', table_name='account')
    op.drop_table('account')
    op.drop_index('verification_identifier_idx', table_name='verification')
    op.drop_table('verification')
    op.drop_table('user')
