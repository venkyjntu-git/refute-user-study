"""
Run once to populate the DB with the sample tasks, e.g.:
    python seed_data.py
"""
from database import Base, engine, SessionLocal
import models
from seed_study import STUDY_TASKS

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

# The next three tasks are INDIRECT ("abstraction-based") questions: the
# description is a real-world scenario rather than a statement of the
# computation, and function/variable names follow the scenario, so Step 1
# also tests whether the student can see the underlying computation (index
# of the maximum, primality, second largest) through the story. Every call
# below was run through sandbox.run_call / sandbox.capture_trace while
# authoring this.

BEST_DAY = dict(
    title="best_day",
    language="python",
    description=(
        "A shop records its sales for a number of consecutive days in the "
        "list `sales`, where `sales[0]` is day 0, `sales[1]` is day 1, and so "
        "on. Write a function `best_day(sales)` that returns the day on which "
        "the shop sold the most. If several days tie for the most sales, "
        "return the earliest of them. You may assume the shop was open for "
        "at least one day."
    ),
    function_signature="def best_day(sales):",
    # Underlying computation: index of the (first) maximum.
    correct_code=(
        "def best_day(sales):\n"
        "    best = 0\n"
        "    for d in range(1, len(sales)):\n"
        "        if sales[d] > sales[best]:\n"
        "            best = d\n"
        "    return best\n"
    ),
    # Bug: compares each day against the PREVIOUS day instead of the best
    # day so far, so it returns the last day that beat its predecessor —
    # e.g. best_day([5, 1, 3]) wrongly returns 2, not 0.
    buggy_code=(
        "def best_day(sales):\n"
        "    best = 0\n"
        "    for d in range(1, len(sales)):\n"
        "        if sales[d] > sales[d - 1]:\n"
        "            best = d\n"
        "    return best\n"
    ),
    # Neither exposes the bug: in both, "beats the previous day" and "beats
    # the best so far" agree at every step.
    trace_sample_inputs=["best_day([7, 2, 1])"],
    trace_data_flow_inputs=["best_day([2, 8, 3])"],
    # Line 4 compares against sales[d - 1] where it should use sales[best].
    buggy_line_numbers=[4],
    trace_prefill_steps=1,
    trace_omit_unchanged_vars=False,
    # The second example demonstrates the tie rule (earliest day).
    io_example_inputs=["best_day([4, 9, 6])", "best_day([5, 5, 2])"],
    # Line 4 shown with the actual fix, as for max_of_three.
    mutation_line_number=4,
    mutation_new_line_text="if sales[d] > sales[best]:",
    mutation_prompt=(
        "In one or two sentences, describe how the function's behavior "
        "changes if line 4 is changed as shown above, compared to the buggy "
        "version shown."
    ),
)

CANNOT_FORM_TEAMS = dict(
    title="cannot_form_teams",
    language="python",
    description=(
        "A coach has `n` players (`n` is at least 2) and wants to split all "
        "of them into teams of equal size, with at least 2 players per team "
        "and at least 2 teams. Write a function `cannot_form_teams(n)` that "
        "returns `True` if this is impossible and `False` if it can be done."
    ),
    function_signature="def cannot_form_teams(n):",
    # Underlying computation: primality — a split exists exactly when
    # n = size * teams with both >= 2, i.e. when n is composite.
    correct_code=(
        "def cannot_form_teams(n):\n"
        "    for size in range(2, n):\n"
        "        if n % size == 0:\n"
        "            return False\n"
        "    return True\n"
    ),
    # Bug: the loop stops before n // 2. For every n >= 2 except 4 this is
    # still enough to find a divisor (or n is prime anyway); for n = 4,
    # range(2, 2) is empty, so it wrongly returns True. 4 is the ONLY
    # counter-example (checked for n = 2..100) — deliberately the hardest
    # Step 3 in the set.
    buggy_code=(
        "def cannot_form_teams(n):\n"
        "    for size in range(2, n // 2):\n"
        "        if n % size == 0:\n"
        "            return False\n"
        "    return True\n"
    ),
    trace_sample_inputs=["cannot_form_teams(15)"],
    trace_data_flow_inputs=["cannot_form_teams(7)"],
    # Line 2 is the too-short range bound.
    buggy_line_numbers=[2],
    trace_prefill_steps=1,
    trace_omit_unchanged_vars=False,
    io_example_inputs=["cannot_form_teams(11)", "cannot_form_teams(9)"],
    # Execution-count variant (no changed line), like first_positive. Uses
    # n = 20 rather than 4 so the question doesn't hand over the only
    # counter-example before Step 3.
    mutation_line_number=3,
    mutation_new_line_text=None,
    mutation_prompt="If `n` is 20, how many times will line 3 be executed?",
)

RUNNER_UP = dict(
    title="runner_up",
    language="python",
    description=(
        "In a contest, every participant gets a different score, recorded in "
        "the list `scores` in no particular order. Write a function "
        "`runner_up(scores)` that returns the score of the participant who "
        "came second. You may assume there are at least two participants."
    ),
    function_signature="def runner_up(scores):",
    # Underlying computation: second-largest of distinct values.
    correct_code=(
        "def runner_up(scores):\n"
        "    first = max(scores[0], scores[1])\n"
        "    second = min(scores[0], scores[1])\n"
        "    for s in scores[2:]:\n"
        "        if s > first:\n"
        "            second = first\n"
        "            first = s\n"
        "        elif s > second:\n"
        "            second = s\n"
        "    return second\n"
    ),
    # Bug: lines 6 and 7 are swapped, so `second` copies the NEW first
    # instead of the old one — e.g. runner_up([1, 2, 3]) wrongly returns 3,
    # not 2. Triggered whenever a new top score appears after the first two.
    buggy_code=(
        "def runner_up(scores):\n"
        "    first = max(scores[0], scores[1])\n"
        "    second = min(scores[0], scores[1])\n"
        "    for s in scores[2:]:\n"
        "        if s > first:\n"
        "            first = s\n"
        "            second = first\n"
        "        elif s > second:\n"
        "            second = s\n"
        "    return second\n"
    ),
    # Neither exposes the bug: the top score is among the first two in both,
    # so lines 6-7 never run.
    trace_sample_inputs=["runner_up([9, 5, 7])"],
    trace_data_flow_inputs=["runner_up([4, 6, 1, 5])"],
    buggy_line_numbers=[6, 7],
    trace_prefill_steps=1,
    trace_omit_unchanged_vars=False,
    io_example_inputs=["runner_up([3, 8])", "runner_up([10, 2, 7])"],
    mutation_line_number=9,
    mutation_new_line_text=None,
    mutation_prompt=(
        "If there are 6 participants, what is the largest number of times "
        "line 9 can be executed?"
    ),
)

# The next two are ABSTRACTION-BASED indirect questions: the story states a
# rule (a streak, a greedy selection policy) that the student has to
# abstract into a computation before reasoning about the code at all.
# Verified through sandbox.run_call / sandbox.capture_trace while authoring.

LONGEST_HOT_STREAK = dict(
    title="longest_hot_streak",
    language="python",
    description=(
        "A weather station records one temperature per day in the list "
        "`temps`. Write a function `longest_hot_streak(temps)` that returns "
        "the length of the longest run of consecutive days on which the "
        "temperature was above 30, or 0 if there were no such days."
    ),
    function_signature="def longest_hot_streak(temps):",
    # Underlying computation: longest run of consecutive elements > 30.
    correct_code=(
        "def longest_hot_streak(temps):\n"
        "    best = 0\n"
        "    run = 0\n"
        "    for t in temps:\n"
        "        if t > 30:\n"
        "            run = run + 1\n"
        "            if run > best:\n"
        "                best = run\n"
        "        if t <= 30:\n"
        "            run = 0\n"
        "    return best\n"
    ),
    # Bug: `best` is only updated when a streak ENDS (on a cool day), so a
    # streak still running when the list ends is never counted — the
    # classic missing-final-update-after-the-loop — e.g.
    # longest_hot_streak([31, 32]) wrongly returns 0, not 2.
    buggy_code=(
        "def longest_hot_streak(temps):\n"
        "    best = 0\n"
        "    run = 0\n"
        "    for t in temps:\n"
        "        if t > 30:\n"
        "            run = run + 1\n"
        "        if t <= 30:\n"
        "            if run > best:\n"
        "                best = run\n"
        "            run = 0\n"
        "    return best\n"
    ),
    # Neither exposes the bug: both lists end on a cool day, so every
    # streak gets closed (and counted) inside the loop.
    trace_sample_inputs=["longest_hot_streak([31, 25, 33, 34, 20])"],
    trace_data_flow_inputs=["longest_hot_streak([35, 28, 29])"],
    # Lines 8-9: the best-so-far update, misplaced under the `t <= 30` branch.
    buggy_line_numbers=[8, 9],
    trace_prefill_steps=1,
    trace_omit_unchanged_vars=False,
    io_example_inputs=[
        "longest_hot_streak([25, 20])", "longest_hot_streak([33, 31, 22, 35])",
    ],
    # No changed line: an abstraction probe about what `best` means in the
    # code as given (rendered without a "changed to" block, like
    # first_positive's).
    mutation_line_number=9,
    mutation_new_line_text=None,
    mutation_prompt="In one sentence, what does `best` hold after the loop ends?",
)

MAX_TALKS = dict(
    title="max_talks",
    language="python",
    description=(
        "A conference lists its talks as `(start, end)` pairs in the list "
        "`talks`, sorted by end time. Going through the list in order, you "
        "attend a talk whenever it starts no earlier than the moment your "
        "previous talk ended (back-to-back talks are fine). Write a function "
        "`max_talks(talks)` that returns how many talks you attend."
    ),
    function_signature="def max_talks(talks):",
    # Underlying computation: greedy activity selection (earliest end first).
    correct_code=(
        "def max_talks(talks):\n"
        "    count = 0\n"
        "    free_at = 0\n"
        "    for start, end in talks:\n"
        "        if start >= free_at:\n"
        "            count = count + 1\n"
        "            free_at = end\n"
        "    return count\n"
    ),
    # Bug: remembers when the attended talk STARTED instead of when it
    # ends, so an overlapping later talk is wrongly accepted — e.g.
    # max_talks([(1, 4), (2, 5)]) wrongly returns 2, not 1.
    buggy_code=(
        "def max_talks(talks):\n"
        "    count = 0\n"
        "    free_at = 0\n"
        "    for start, end in talks:\n"
        "        if start >= free_at:\n"
        "            count = count + 1\n"
        "            free_at = start\n"
        "    return count\n"
    ),
    # Neither exposes the bug: no two talks overlap in either list, so
    # remembering start vs end never changes which talks are accepted.
    trace_sample_inputs=["max_talks([(1, 2), (3, 5), (6, 8)])"],
    trace_data_flow_inputs=["max_talks([(2, 3), (4, 6)])"],
    # Line 7 stores `start` where it should store `end`.
    buggy_line_numbers=[7],
    trace_prefill_steps=1,
    trace_omit_unchanged_vars=False,
    # The first example demonstrates the back-to-back rule.
    io_example_inputs=["max_talks([(1, 3), (3, 4)])", "max_talks([(1, 10)])"],
    mutation_line_number=7,
    mutation_new_line_text="free_at = end",
    mutation_prompt=(
        "In one or two sentences, describe how the function's behavior "
        "changes if line 7 is changed as shown above, compared to the buggy "
        "version shown."
    ),
)

# One more abstraction-based task, same authoring conventions. Its claimed
# counter-example set was checked by an exhaustive sweep (minutes 1..1440)
# while authoring.

PARKING_FEE = dict(
    title="parking_fee",
    language="python",
    description=(
        "A car park charges 20 for the first hour and 10 for each additional "
        "hour. Any part of an hour counts as a full hour. The fee for a "
        "single stay never exceeds 100. Write a function "
        "`parking_fee(minutes)` that returns the fee for parking `minutes` "
        "minutes. You may assume `minutes` is at least 1."
    ),
    function_signature="def parking_fee(minutes):",
    # Underlying computation: ceiling division to whole hours, then a capped
    # linear fee.
    correct_code=(
        "def parking_fee(minutes):\n"
        "    hours = (minutes + 59) // 60\n"
        "    fee = 20 + (hours - 1) * 10\n"
        "    if fee > 100:\n"
        "        fee = 100\n"
        "    return fee\n"
    ),
    # Bug: `minutes // 60 + 1` rounds up correctly EXCEPT on exact whole
    # hours, where it adds a phantom extra hour — e.g. parking_fee(60)
    # wrongly returns 30, not 20. Counter-examples are exactly 60, 120, ...,
    # 480: from 540 minutes up both versions hit the 100 cap, which hides it.
    buggy_code=(
        "def parking_fee(minutes):\n"
        "    hours = minutes // 60 + 1\n"
        "    fee = 20 + (hours - 1) * 10\n"
        "    if fee > 100:\n"
        "        fee = 100\n"
        "    return fee\n"
    ),
    # Neither is a whole number of hours.
    trace_sample_inputs=["parking_fee(90)"],
    trace_data_flow_inputs=["parking_fee(200)"],
    buggy_line_numbers=[2],
    trace_prefill_steps=1,
    trace_omit_unchanged_vars=False,
    # The second example demonstrates the cap.
    io_example_inputs=["parking_fee(30)", "parking_fee(1000)"],
    mutation_line_number=2,
    mutation_new_line_text="hours = (minutes + 59) // 60",
    mutation_prompt=(
        "In one or two sentences, describe how the function's behavior "
        "changes if line 2 is changed as shown above, compared to the buggy "
        "version shown."
    ),
)
SAMPLE_TASKS = [
    MAX_OF_THREE, SMALLEST, COUNT_POSITIVES, FIRST_POSITIVE,
    BEST_DAY, CANNOT_FORM_TEAMS, RUNNER_UP,
    LONGEST_HOT_STREAK, MAX_TALKS,
    PARKING_FEE,
] + STUDY_TASKS

# Fields that describe how step 2 is presented rather than what the task is;
# safe to refresh on an already-seeded task so an existing dev DB picks up
# changes without being rebuilt.
TRACE_CONFIG_FIELDS = (
    "trace_sample_inputs", "trace_data_flow_inputs", "buggy_line_numbers",
    "trace_prefill_steps", "trace_omit_unchanged_vars",
    "io_example_inputs",
    "mutation_line_number", "mutation_new_line_text", "mutation_prompt",
)

# Study-variant wording that the WG may revise after the pilot (and the
# code-mixed text, which arrives later). Code is deliberately NOT refreshed:
# changing a program under existing sessions would corrupt their analysis.
STUDY_CONTENT_FIELDS = (
    "description", "description_mixed", "input_validator", "step3_max_attempts",
)


def _seed_one(db, sample_task: dict) -> None:
    existing = db.query(models.Task).filter_by(title=sample_task["title"]).first()
    if existing:
        changed = []
        fields = TRACE_CONFIG_FIELDS
        if sample_task.get("variant_key"):
            fields = fields + STUDY_CONTENT_FIELDS
        for field in fields:
            if getattr(existing, field) != sample_task[field]:
                setattr(existing, field, sample_task[field])
                changed.append(field)
        if changed:
            db.commit()
            print(f"Task '{sample_task['title']}' (id={existing.id}) already exists; "
                  f"refreshed config: {', '.join(changed)}")
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
