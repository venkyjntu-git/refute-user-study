# Refute-Problem User Study — What It Measures and How

## Background
In **CS1**, a **Refute problem** involves a task description and a buggy program. The student must find a **counter-example**—an input for which the buggy program produces the wrong output.

A **\*\*Refute problem\*\*** in a CS1 setting gives a student:

\- a task description (what the function is supposed to do), and

\- a single buggy implementation of that function,

and asks the student to find a **\*\*counter-example\*\***: an input on which the

buggy code's output differs from what the correct code would produce. Doing

this well requires the student to (a) understand what the function is

*\*supposed\** to do, (b) read/trace the buggy code accurately, and (c) reason

about where the two diverge.

This study breaks that single ask into three separate, individually-timed

steps, so we can see *\*where\** the difficulty actually lives — do students

struggle to understand the spec, to trace code, or to construct a

distinguishing input, or all three?

## The three steps

### Step 1 — Input/output pairs (do they understand the spec?)

The student is shown only the **task description** (no code at all) and
must supply **three (input, output) pairs** that they believe are correct
for the intended behavior. Each pair is written as:

```
funcname(arguments)
expected output
```

The system runs each of the student's calls against the **correct**
reference implementation (hidden from the student) and checks whether the
student's expected output matches. The student must get all three pairs
correct before moving on; incorrect pairs are shown back with the actual
output, and the student may revise and resubmit.

**What this measures:** whether the student has correctly internalized the
specification, independent of any code at all. If a student can't produce
three correct (input, output) pairs, later confusion about the buggy code
is at least partly a spec-comprehension problem, not (only) a code-tracing
problem.

**Example** (task: "write `max_of_three(a, b, c)` that returns the largest
of three integers"):

| Student writes | System checks against correct code | Result |
|---|---|---|
| `max_of_three(1, 2, 3)` → `3` | correct code returns `3` | ✅ correct |
| `max_of_three(5, 2, 1)` → `5` | correct code returns `5` | ✅ correct |
| `max_of_three(2, 2, 2)` → `2` | correct code returns `2` | ✅ correct |

All three match, so the student unlocks Step 2.

---

### Step 2 — Trace the buggy code (can they read code accurately?)

The student is now shown the **buggy implementation** for the first time,
along with **two fixed sample inputs** chosen by the task author. For each
sample input, the student hand-traces the code and writes down what they
believe it outputs — no explanation or reasoning required, just the traced
result.

Behind the scenes, the system also runs each sample input against the
buggy code and records whether the student's traced output matches the
buggy code's *actual* output. This isn't used to block progress (tracing
correctly isn't a gate — getting it wrong is itself useful data), but it
gives a per-student "trace accuracy" signal for analysis.

**What this measures:** pure code-reading/tracing ability, on inputs the
researcher has already chosen — separate from the harder job of *inventing*
a distinguishing input in Step 3.

**Example:** the buggy implementation has a bug where the `elif` skips
checking `c` once `b` has already replaced `a`:

```python
def max_of_three(a, b, c):
    largest = a
    if b > largest:
        largest = b
    elif c > largest:      # bug: should be `if`, not `elif`
        largest = c
    return largest
```

Sample inputs given to the student to trace:

| Sample input | Student's traced output | Actual buggy output | Result |
|---|---|---|---|
| `max_of_three(1, 2, 3)` | `3` | `3` | matches (bug doesn't manifest here) |
| `max_of_three(3, 2, 1)` | `3` | `3` | matches |

Note these two sample inputs happen to *not* expose the bug — that's
intentional; Step 2 is about tracing skill, not about finding the flaw.
The student moves on to Step 3 regardless of trace accuracy.

---

### Step 3 — Find a counter-example (can they construct a distinguishing input?)

The student now supplies a single input of their own choosing. The system
runs that exact call against **both** the correct code and the buggy code
and reports both outputs plus a verdict: the input is a valid
counter-example if and only if the two outputs differ.

**What this measures:** the actual refutation skill — synthesizing an input
that exposes the discrepancy, which requires combining the correct mental
model from Step 1 with an understanding of the buggy code's actual
behavior from Step 2.

**Example:** the bug is triggered whenever `b` is *not* the largest but
does exceed `a`, so the `elif` branch checking `c` never runs, and the
true largest value (`c`) is missed. A student who reasons this through
might submit:

| Student submits | Correct code output | Buggy code output | Verdict |
|---|---|---|---|
| `max_of_three(1, 3, 5)` | `5` | `3` | ✅ valid counter-example (outputs differ) |

If a student instead submits `max_of_three(1, 2, 3)` again, both outputs
would be `3` — not a counter-example — and they'd be told to try a
different input.

## What gets measured, per step

For every step, the app logs a server timestamp the moment the step is
**shown** and another the moment the student **submits**, plus every
submission's content and correctness. This lets the analysis compute, per
student and per task:

- time spent forming I/O pairs (spec comprehension time)
- number of attempts needed to get all three I/O pairs right
- time spent tracing the buggy code, and whether the trace was accurate
- time spent finding a counter-example, and how many attempts it took
- whether the *first* counter-example attempt succeeded (a proxy for how
  directly the student reasoned to it, versus trial-and-error)

Comparing these across students and across tasks is the core of the
difficulty analysis: e.g., a task where Step 1 is fast and correct but
Step 3 takes many attempts suggests the difficulty is in constructing a
distinguishing input, not in understanding the spec — whereas slow, error-
prone Step 1 attempts point to a specification the students didn't
understand well enough to reliably reason about the bug at all.