from alembic import command
from sqlalchemy import func, inspect, select, text

from supportagent.db.base import Base
from supportagent.db.models.mcp import McpServer, McpToolPolicy
from supportagent.db.session import SessionLocal, engine

BASELINE = "863e47af17d2"


def test_migrations_create_every_model_table(database):
    tables = set(inspect(engine).get_table_names())
    assert set(Base.metadata.tables) <= tables


def test_models_and_migrations_are_in_sync(database):
    command.check(database)


def test_seed_migration_adds_default_mcp_servers_and_policies(database, clean_db):
    command.downgrade(database, BASELINE)
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM mcp_servers"))
    command.upgrade(database, "head")

    with SessionLocal() as session:
        servers = session.scalars(
            select(McpServer.server_name).order_by(McpServer.server_name)
        ).all()
        policy_count = session.scalar(select(func.count()).select_from(McpToolPolicy))
        create_message = session.get(McpToolPolicy, ("teams_mcp", "create_message"))

    assert servers == ["teams_mcp", "time_mcp", "weather_mcp"]
    assert policy_count == 21
    assert create_message.enabled is False
