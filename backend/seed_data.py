"""
Run once to populate the DB with a sample task, e.g.:
    python seed_data.py
"""
from database import Base, engine, SessionLocal
import models

Base.metadata.create_all(bind=engine)

SAMPLE_TASK = dict(
    title="max_of_three",
    description=(
        "Write a function `max_of_three(a, b, c)` that takes three integers "
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
    trace_sample_inputs=["max_of_three(1, 2, 3)", "max_of_three(3, 2, 1)"],
)


def main():
    db = SessionLocal()
    try:
        existing = db.query(models.Task).filter_by(title=SAMPLE_TASK["title"]).first()
        if existing:
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
