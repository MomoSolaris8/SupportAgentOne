from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext

import supportagent.db.models  # noqa: F401
from supportagent.db.base import Base
from supportagent.db.session import engine

modeled = set(Base.metadata.tables)


def include_object(obj, name, type_, reflected, compare_to):
    table = obj if type_ == "table" else obj.table
    return table.name in modeled


with engine.connect() as conn:
    ctx = MigrationContext.configure(
        conn, opts={"compare_type": True, "include_object": include_object}
    )
    diffs = compare_metadata(ctx, Base.metadata)

print("check table:", ", ".join(sorted(modeled)))
if not diffs:
    print("✅ Model and database are in sync")
for d in diffs:
    print("❌", d)
