from alembic import command
from sqlalchemy import inspect

from supportagent.db.base import Base
from supportagent.db.session import engine


def test_migrations_create_every_model_table(database):
    tables = set(inspect(engine).get_table_names())
    assert set(Base.metadata.tables) <= tables


def test_models_and_migrations_are_in_sync(database):
    command.check(database)
