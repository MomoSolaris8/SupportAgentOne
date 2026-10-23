import os
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

PROJECT_ROOT = Path(__file__).resolve().parents[2]
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql://supportagent:supportagent@localhost:5433/supportagent_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


def _admin_url() -> str:
    return TEST_DATABASE_URL.rsplit("/", 1)[0] + "/postgres"


@pytest.fixture(scope="session")
def database():
    db_name = TEST_DATABASE_URL.rsplit("/", 1)[1]
    assert db_name.endswith("_test"), (
        f"refusing to recreate non-test database {db_name!r}"
    )

    with psycopg.connect(_admin_url(), autocommit=True) as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
        admin.execute(f'CREATE DATABASE "{db_name}"')

    alembic_config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(alembic_config, "head")
    yield alembic_config

    from supportagent.db.session import engine

    engine.dispose()
    with psycopg.connect(_admin_url(), autocommit=True) as admin:
        admin.execute(f'DROP DATABASE "{db_name}" WITH (FORCE)')


@pytest.fixture
def clean_db(database):
    yield
    from supportagent.db.base import Base
    from supportagent.db.session import engine

    tables = ", ".join(table.name for table in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))
