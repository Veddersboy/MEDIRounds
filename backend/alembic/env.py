"""Alembic migration runner for async production databases and tests."""
import asyncio
import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

url = config.get_main_option("sqlalchemy.url")
if url == "sqlite:///placeholder.db":
    from app.database import settings
    url = settings.DATABASE_URL


def migrate_offline():
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True,
                      dialect_opts={"paramstyle": "named"}, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()

def migrate_connection(connection):
    context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
    with context.begin_transaction():
        context.run_migrations()

async def migrate_async():
    engine = async_engine_from_config({"sqlalchemy.url": url}, prefix="sqlalchemy.", poolclass=pool.NullPool)
    async with engine.connect() as connection:
        await connection.run_sync(migrate_connection)
    await engine.dispose()

def migrate_sync():
    engine = engine_from_config({"sqlalchemy.url": url}, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with engine.connect() as connection:
        migrate_connection(connection)
    engine.dispose()

if context.is_offline_mode():
    migrate_offline()
elif url.startswith(("postgresql+asyncpg:", "sqlite+aiosqlite:")):
    asyncio.run(migrate_async())
else:
    migrate_sync()
