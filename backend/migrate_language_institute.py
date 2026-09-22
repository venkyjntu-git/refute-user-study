"""
Add the language-picker columns to an existing DB: tasks.language and
study_sessions.institute.

`Base.metadata.create_all` creates missing TABLES but never adds columns to a
table that already exists, so an existing refute_study.db will not pick these
up on its own (same situation as migrate_trace.py). Idempotent — run it as
many times as you like:

    python migrate_language_institute.py
"""
from sqlalchemy import inspect, text

from database import engine


def _table_migrations(dialect: str) -> dict:
    return {
        "tasks": {
            # Existing rows default to "python" — every task seeded before
            # this migration existed was a Python task.
            "language": "VARCHAR NOT NULL DEFAULT 'python'",
        },
        "study_sessions": {
            # Nullable: existing sessions predate the institute field and
            # have no honest value to backfill.
            "institute": "VARCHAR",
        },
    }


def main():
    inspector = inspect(engine)
    print(f"database: {engine.dialect.name}")

    with engine.begin() as conn:
        for table, columns in _table_migrations(engine.dialect.name).items():
            if table not in inspector.get_table_names():
                print(f"no {table} table yet — nothing to migrate (create_all will "
                      f"build it with these columns already in place)")
                continue
            existing = {col["name"] for col in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name in existing:
                    print(f"{table}.{name} already present; skipping")
                    continue
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                print(f"added {table}.{name}")


if __name__ == "__main__":
    main()
