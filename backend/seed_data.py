"""
Run once to populate the DB with a sample task, e.g.:
    python seed_data.py
"""
from database import Base, engine, SessionLocal
import models

Base.metadata.create_all(bind=engine)

SAMPLE_TASK = dict(
    title="max_of_three",
    language="python",
    description=(
        "Consider a function `max_of_three(a, b, c)` that takes three integers "
        "and returns the largest of the three."
    ),
    function_signature="def max_of_three(a, b, c):",
    correct_code=(
        "def max_of_three(a, b, c):\n"
        "    largest = a\n"
        "    if b > largest:\n"
        "        largest = b\n"
        "    if c > largest:\n"
        "        largest = c\n"
        "    return largest\n"
    ),
    # Bug: uses elif, so if c is the largest but b > a, c is never checked.
    buggy_code=(
        "def max_of_three(a, b, c):\n"
        "    largest = a\n"
        "    if b > largest:\n"
        "        largest = b\n"
        "    elif c > largest:\n"
        "        largest = c\n"
        "    return largest\n"
    ),
    # One control-flow input, one data-flow input — both instructor-provided,
    # and they must be different calls from each other (see trace_table.py's
    # module docstring for why: the data-flow table reveals its call's
    # execution path outright, which is only safe because it isn't the call
    # the control-flow question is hiding). Neither exposes the bug, per
    # Method.md: step 2 measures tracing skill, not bug-finding.
    trace_sample_inputs=["max_of_three(2, 1, 3)"],
    trace_data_flow_inputs=["max_of_three(1, 5, 3)"],
    # Line 5 of buggy_code is the `elif` that should be an `if`. Used only for
    # analysis (scoring the trace at the buggy line), never shown to students.
    buggy_line_numbers=[5],
    trace_prefill_steps=1,
    trace_omit_unchanged_vars=False,
)

# Fields that describe how step 2 is presented rather than what the task is;
# safe to refresh on an already-seeded task so an existing dev DB picks up
# changes without being rebuilt.
TRACE_CONFIG_FIELDS = (
    "trace_sample_inputs", "trace_data_flow_inputs", "buggy_line_numbers",
    "trace_prefill_steps", "trace_omit_unchanged_vars",
)


def main():
    db = SessionLocal()
    try:
        existing = db.query(models.Task).filter_by(title=SAMPLE_TASK["title"]).first()
        if existing:
            changed = []
            for field in TRACE_CONFIG_FIELDS:
                if getattr(existing, field) != SAMPLE_TASK[field]:
                    setattr(existing, field, SAMPLE_TASK[field])
                    changed.append(field)
            if changed:
                db.commit()
                print(f"Task '{SAMPLE_TASK['title']}' (id={existing.id}) already exists; "
                      f"refreshed trace config: {', '.join(changed)}")
            else:
                print(f"Task '{SAMPLE_TASK['title']}' already exists (id={existing.id}); skipping.")
            return
        task = models.Task(**SAMPLE_TASK)
        db.add(task)
        db.commit()
        db.refresh(task)
        print(f"Inserted task id={task.id}: {task.title}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
