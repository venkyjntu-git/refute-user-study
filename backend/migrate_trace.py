"""
Add the step-2 trace-table columns to an existing tasks table.

`Base.metadata.create_all` creates missing TABLES but never adds columns to a
table that already exists, so an existing refute_study.db will not pick these
up on its own. Idempotent — run it as many times as you like:

    python migrate_trace.py
"""
from sqlalchemy import inspect, text

from database import engine

def _new_columns(dialect: str) -> dict:
    # SQLite spells boolean false as 0; Postgres wants the keyword.
    false_literal = "0" if dialect == "sqlite" else "FALSE"
    return {
        "buggy_line_numbers": "JSON",
        "trace_prefill_steps": "INTEGER NOT NULL DEFAULT 1",
        "trace_omit_unchanged_vars": f"BOOLEAN NOT NULL DEFAULT {false_literal}",
    }


def main():
    inspector = inspect(engine)
    print(f"database: {engine.dialect.name}")
    if "tasks" not in inspector.get_table_names():
        print("no tasks table yet — nothing to migrate (create_all will build it "
              "with these columns already in place)")
        return

    existing = {col["name"] for col in inspector.get_columns("tasks")}
    with engine.begin() as conn:
        for name, ddl in _new_columns(engine.dialect.name).items():
            if name in existing:
                print(f"tasks.{name} already present; skipping")
                continue
            conn.execute(text(f"ALTER TABLE tasks ADD COLUMN {name} {ddl}"))
            print(f"added tasks.{name}")


if __name__ == "__main__":
    main()
