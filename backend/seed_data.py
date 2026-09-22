"""
Run once to populate the DB with the sample tasks, e.g.:
    python seed_data.py
"""
from database import Base, engine, SessionLocal
import models

Base.metadata.create_all(bind=engine)

MAX_OF_THREE = dict(
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
    # Step 1 example reveal: two worked examples, run against correct_code,
    # offered only after a first wrong attempt (see main.py's
    # reveal_io_examples). Distinct from the student's own eventual 3 pairs
    # by construction (they pick their own values), and from the Step 2
    # sample inputs above (different purpose, no overlap required, but kept
    # distinct anyway for clarity).
    io_example_inputs=["max_of_three(4, 9, 2)", "max_of_three(-3, -1, -7)"],
    # Step 2 mutation question: line 5 is the buggy `elif` (see
    # buggy_line_numbers above) — shown hypothetically changed back to `if`,
    # i.e. the actual fix, so the reflection question is genuinely about the
    # fix rather than an arbitrary unrelated mutation.
    mutation_line_number=5,
    mutation_new_line_text="if c > largest:",
    mutation_prompt=(
        "In one or two sentences, describe how the function's behavior "
        "changes if line 5 is changed as shown above, compared to the buggy "
        "version shown."
    ),
)

# The next three tasks are the worked examples from the "Code Comprehension
# proxy" mockup: each pairs a task description with a buggy implementation
# and a mutation-question prompt. Every call below was actually run through
# sandbox.run_call / sandbox.capture_trace while authoring this (not just
# hand-traced) — see the session notes for the verification transcript.

SMALLEST = dict(
    title="smallest",
    language="python",
    description=(
        "Write a function `smallest(nums)` that returns the smallest number "
        "in the list `nums`. You may assume `nums` contains at least one "
        "number."
    ),
    function_signature="def smallest(nums):",
    correct_code=(
        "def smallest(nums):\n"
        "    result = nums[0]\n"
        "    for i in range(1, len(nums)):\n"
        "        if nums[i] < result:\n"
        "            result = nums[i]\n"
        "    return result\n"
    ),
    # Bug: the loop bound is `len(nums) - 1`, so the LAST element is never
    # compared — e.g. smallest([10, 20, 5]) wrongly returns 10, not 5.
    buggy_code=(
        "def smallest(nums):\n"
        "    result = nums[0]\n"
        "    for i in range(1, len(nums) - 1):\n"
        "        if nums[i] < result:\n"
        "            result = nums[i]\n"
        "    return result\n"
    ),
    # Neither exposes the bug: the true minimum isn't the last element in
    # either list, so skipping it doesn't change the result.
    trace_sample_inputs=["smallest([5, 3, 8])"],
    trace_data_flow_inputs=["smallest([9, 2, 6, 4])"],
    # Line 3 is the `range(1, len(nums) - 1)` off-by-one.
    buggy_line_numbers=[3],
    trace_prefill_steps=1,
    trace_omit_unchanged_vars=False,
    io_example_inputs=["smallest([10, 20, 5])", "smallest([-3, -7, -1])"],
    # Mockup's mutation question: line 4's comparison flipped from < to >
    # (turns "find the smallest" into "find the largest", still under the
    # same off-by-one loop bound).
    mutation_line_number=4,
    mutation_new_line_text="if nums[i] > result:",
    mutation_prompt="Describe the resulting code in one line.",
)

COUNT_POSITIVES = dict(
    title="count_positives",
    language="python",
    description=(
        "Write a function `count_positives(nums)` that returns how many "
        "numbers in the list `nums` are strictly greater than zero."
    ),
    function_signature="def count_positives(nums):",
    correct_code=(
        "def count_positives(nums):\n"
        "    total = 0\n"
        "    for x in nums:\n"
        "        if x > 0:\n"
        "            total = total + 1\n"
        "    return total\n"
    ),
    # Bug: `x >= 0` counts zero as positive too, which the spec ("strictly
    # greater than zero") rules out — e.g. count_positives([0, 1, 2])
    # wrongly returns 3, not 2.
    buggy_code=(
        "def count_positives(nums):\n"
        "    total = 0\n"
        "    for x in nums:\n"
        "        if x >= 0:\n"
        "            total = total + 1\n"
        "    return total\n"
    ),
    # Neither list contains a zero, so the bug never manifests.
    trace_sample_inputs=["count_positives([1, -2, 3, -4])"],
    trace_data_flow_inputs=["count_positives([-5, -6, -7])"],
    # Line 4 is the `x >= 0` that should be `x > 0`.
    buggy_line_numbers=[4],
    trace_prefill_steps=1,
    trace_omit_unchanged_vars=False,
    io_example_inputs=["count_positives([2, -1, 5])", "count_positives([-10, -20])"],
    # Mockup's mutation question: line 5 changed from counting (+1) to
    # summing (+x) — turns "how many are non-negative" into "what do the
    # non-negative ones add up to".
    mutation_line_number=5,
    mutation_new_line_text="total = total + x",
    mutation_prompt="Describe the resulting code.",
)

FIRST_POSITIVE = dict(
    title="first_positive",
    language="python",
    description=(
        "Write a function `first_positive(nums)` that returns the first "
        "element of the list `nums` that is strictly greater than zero. If "
        "no such element exists, return `None`."
    ),
    function_signature="def first_positive(nums):",
    correct_code=(
        "def first_positive(nums):\n"
        "    for x in nums:\n"
        "        if x > 0:\n"
        "            return x\n"
        "    return None\n"
    ),
    # Bug: never stops after finding a positive — keeps overwriting `result`
    # on every later positive, so it returns the LAST positive, not the
    # first — e.g. first_positive([2, -1, 7]) wrongly returns 7, not 2.
    buggy_code=(
        "def first_positive(nums):\n"
        "    result = None\n"
        "    for x in nums:\n"
        "        if x > 0:\n"
        "            result = x\n"
        "    return result\n"
    ),
    # Each list has at most one positive number, so "first" and "last"
    # positive coincide and the bug never manifests.
    trace_sample_inputs=["first_positive([-1, -2, 5, -3])"],
    trace_data_flow_inputs=["first_positive([-5, -6, 8])"],
    # Line 5 is where the wrong "keep overwriting" behavior shows up (the
    # actual fix is a missing early return, not a different comparison, but
    # this is the line whose behavior diverges from intent each time the
    # loop runs past the first positive).
    buggy_line_numbers=[5],
    trace_prefill_steps=1,
    trace_omit_unchanged_vars=False,
    io_example_inputs=["first_positive([-1, -2, -3])", "first_positive([4, -5, -6])"],
    # Mockup's mutation question for this task isn't a "line changed to X"
    # prompt at all — it's a pure execution-count question about the code
    # AS GIVEN, and it names its own line number. mutation_new_line_text
    # stays unset; Step2Trace.jsx renders this variant without a "changed
    # to" block (see its comment there).
    mutation_line_number=5,
    mutation_new_line_text=None,
    mutation_prompt="If `nums` has 10 elements, how many times will line 5 be executed?",
)

SAMPLE_TASKS = [MAX_OF_THREE, SMALLEST, COUNT_POSITIVES, FIRST_POSITIVE]

# Fields that describe how step 2 is presented rather than what the task is;
# safe to refresh on an already-seeded task so an existing dev DB picks up
# changes without being rebuilt.
TRACE_CONFIG_FIELDS = (
    "trace_sample_inputs", "trace_data_flow_inputs", "buggy_line_numbers",
    "trace_prefill_steps", "trace_omit_unchanged_vars",
    "io_example_inputs",
    "mutation_line_number", "mutation_new_line_text", "mutation_prompt",
)


def _seed_one(db, sample_task: dict) -> None:
    existing = db.query(models.Task).filter_by(title=sample_task["title"]).first()
    if existing:
        changed = []
        for field in TRACE_CONFIG_FIELDS:
            if getattr(existing, field) != sample_task[field]:
                setattr(existing, field, sample_task[field])
                changed.append(field)
        if changed:
            db.commit()
            print(f"Task '{sample_task['title']}' (id={existing.id}) already exists; "
                  f"refreshed trace config: {', '.join(changed)}")
        else:
            print(f"Task '{sample_task['title']}' already exists (id={existing.id}); skipping.")
        return
    task = models.Task(**sample_task)
    db.add(task)
    db.commit()
    db.refresh(task)
    print(f"Inserted task id={task.id}: {task.title}")


def main():
    db = SessionLocal()
    try:
        for sample_task in SAMPLE_TASKS:
            try:
                _seed_one(db, sample_task)
            except Exception as e:
                db.rollback()
                print(f"Error seeding '{sample_task['title']}': {e}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
