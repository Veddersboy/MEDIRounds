from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


def test_migrations_create_fresh_database(tmp_path):
    from pathlib import Path

    backend_root = Path(__file__).resolve().parents[1]
    db_path = tmp_path / "fresh.db"
    url = f"sqlite:///{db_path.as_posix()}"

    config = Config(str(backend_root / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", url)
    command.upgrade(config, "head")

    engine = create_engine(url)
    tables = set(inspect(engine).get_table_names())
    assert {"users", "chat_sessions", "messages", "citations", "user_settings"} <= tables
    with engine.connect() as conn:
        assert conn.execute(text("SELECT version_num FROM alembic_version")).scalar_one() == "0001"
    engine.dispose()

    command.upgrade(config, "head")
