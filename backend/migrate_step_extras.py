"""
Add the columns for three additive study features to an existing DB:
- tasks.io_example_inputs                                (Step 1 example reveal)
- tasks.mutation_line_number / mutation_new_line_text /
  mutation_prompt                                          (Step 2 mutation question)
- study_sessions.io_examples_shown                         (Step 1 reveal state)

`Base.metadata.create_all` creates missing TABLES but never adds columns to a
table that already exists, so an existing refute_study.db will not pick these
up on its own (same situation as migrate_trace.py / migrate_language_institute.py).
Idempotent — run it as many times as you like:

    python migrate_step_extras.py
"""
from sqlalchemy import inspect, text

from database import engine


def _table_migrations(dialect: str) -> dict:
    false_literal = "0" if dialect == "sqlite" else "FALSE"
    return {
        "tasks": {
            "io_example_inputs": "JSON",
            "mutation_line_number": "INTEGER",
            "mutation_new_line_text": "TEXT",
            "mutation_prompt": "TEXT",
        },
        "study_sessions": {
            # Existing sessions predate the reveal feature entirely, so
            # "not yet shown" (False) is the honest backfill value, not a
            # guess — every one of them genuinely never saw a reveal.
            "io_examples_shown": f"BOOLEAN NOT NULL DEFAULT {false_literal}",
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
