"""
Check the study task content in seed_study.py by actually running it:

- every Step 2 input and every Step 1 example input gives the same output on
  the reference solution and on BOTH buggy programs (none is a
  counter-example);
- every listed counter-example really is one, for its own bug;
- each form's validator accepts the Step 2 inputs' shape where relevant, the
  examples and counter-examples, and the contextualized validator rejects the
  listed implausible inputs;
- the condition table balances form x bug per problem in every 4 rows, and
  order in every 8.

Run from backend/ with the venv python:  python check_study_tasks.py
Exits non-zero on any failure.
"""
import sys
from collections import Counter

import assignment
import sandbox
from seed_study import STUDY_PROBLEMS, STUDY_TASKS

failures = []


def check(ok: bool, message: str) -> None:
    print(("  ok   " if ok else "  FAIL ") + message)
    if not ok:
        failures.append(message)


def outputs(code: str, call: str) -> str:
    result = sandbox.run_call(code, call)
    return result.value_repr if result.ok else f"<error: {result.error}>"


for problem in STUDY_PROBLEMS:
    print(f"\n{problem['key']} ({problem['function_signature']})")
    ref = problem["correct_code"]
    neutral = (problem["trace_sample_inputs"] + problem["trace_data_flow_inputs"]
               + problem["io_example_inputs"])
    for bug_kind, bug in problem["bugs"].items():
        for call in neutral:
            want, got = outputs(ref, call), outputs(bug["code"], call)
            check(want == got and not want.startswith("<error"),
                  f"{bug_kind}: {call} not a counter-example (ref {want}, buggy {got})")
        for call in bug["counterexamples"]:
            want, got = outputs(ref, call), outputs(bug["code"], call)
            check(want != got, f"{bug_kind}: {call} IS a counter-example (ref {want}, buggy {got})")
            for form, spec in problem["forms"].items():
                reason = sandbox.run_validator(spec["input_validator"], call)
                check(reason is None, f"{form} validator accepts {call} ({reason})")
    for form, spec in problem["forms"].items():
        for call in problem["io_example_inputs"]:
            reason = sandbox.run_validator(spec["input_validator"], call)
            check(reason is None, f"{form} validator accepts example {call} ({reason})")
    for call in problem["implausible_examples"]:
        d = sandbox.run_validator(problem["forms"]["direct"]["input_validator"], call)
        c = sandbox.run_validator(problem["forms"]["contextualized"]["input_validator"], call)
        check(c is not None, f"contextualized validator rejects {call} ({c})")
        print(f"         (direct validator on it: {d or 'accepted'})")

print("\nVariants")
keys = sorted(t["variant_key"] for t in STUDY_TASKS)
check(len(keys) == 8 and len(set(keys)) == 8, f"8 distinct variants: {keys}")

print("\nCondition table")
for start in (0, 4):
    cells = Counter()
    for row in range(start, start + 4):
        for key in assignment.variants_for_row(row):
            cells[key] += 1
    check(sorted(cells) == keys and set(cells.values()) == {1},
          f"rows {start}-{start + 3}: each variant once")
orders = Counter(assignment.CONDITIONS[r][4] for r in range(8))
check(set(orders.values()) == {4}, f"order balanced over 8 rows: {dict(orders)}")
for row in range(8):
    forms = sorted(k.split("_")[1] for k in assignment.variants_for_row(row))
    check(forms == ["Contextualized", "Direct"], f"row {row}: one Direct, one Contextualized")

print()
if failures:
    print(f"{len(failures)} check(s) FAILED")
    sys.exit(1)
print("all checks passed")
