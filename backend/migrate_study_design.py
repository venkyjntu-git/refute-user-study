"""
Add the columns for the counterbalanced WG study design to an existing DB:
- tasks.variant_key / problem_key / form / bug_kind     (which variant a row is)
- tasks.description_mixed                                 (code-mixed spec text)
- tasks.input_validator                                   (validity / plausibility)
- tasks.step3_max_attempts                                (study-mode Step 3)
- study_sessions.participant_id / position                (link to Participant)

The new tables (participants, spec_view_events) need nothing here:
`Base.metadata.create_all` creates missing TABLES, it just never adds columns
to a table that already exists (same situation as migrate_step_extras.py).
Idempotent — run it as many times as you like:

    python migrate_study_design.py
"""
from sqlalchemy import inspect, text

from database import Base, engine
import models  # noqa: F401  (registers the new tables on Base.metadata)

MIGRATIONS = {
    "tasks": {
        "variant_key": "VARCHAR",
        "problem_key": "VARCHAR",
        "form": "VARCHAR",
        "bug_kind": "VARCHAR",
        "description_mixed": "JSON",
        "input_validator": "TEXT",
        "step3_max_attempts": "INTEGER",
    },
    "study_sessions": {
        # Plain column, no FK constraint: SQLite can't add one via ALTER
        # TABLE, and the ORM relationship doesn't need it to work.
        "participant_id": "INTEGER",
        "position": "INTEGER",
    },
}


def main():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    print(f"database: {engine.dialect.name}")

    with engine.begin() as conn:
        for table, columns in MIGRATIONS.items():
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
