# Refute-Problem User Study — What It Measures and How

## Background

A **\*\*Refute problem\*\*** in our study involves:

\- a task description (what the function is supposed to do), and

\- a single buggy implementation of that function,

and asks the student to find a **\*\*counter-example\*\***: an input on which the

buggy code's output differs from what the correct code would produce
<!-- In **CS1**, a **Refute problem** involves a task description and a buggy program. The student must find a **counter-example**, an input for which the buggy program produces the wrong output. -->

Doing this well requires the student to 

(a) understand what the function is  *\*supposed\** to do, 

(b) read/trace the buggy code accurately, and 

(c) reason about where the two differ in functionality.

This study breaks that single ask into three separate, individually-timed steps, so we can see *\*where\** the difficulty actually lives — do students struggle to understand the specification, to understand/trace code, or to construct a distinguishing input, or all three?

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
correct before moving on. Each pair is marked correct or incorrect and the
student may revise and resubmit as many times as they need — but **the
reference implementation's output is never shown**. If a call cannot be run at
all (wrong function name, wrong number of arguments, bad syntax) the student is
told only to check the name and arguments, not the underlying Python error.

The real output and the true
error text are still recorded server-side for analysis. This mirrors the
no-feedback rule in Step 2, for the same reason — later steps have to measure
unaided reasoning.

**What this measures:** whether the student has correctly internalized the
specification, independent of any code at all — and, through the attempt
count, how readily they got there unaided. If a student can't produce
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
sample input the student fills in an **execution trace table**: one row per
line that actually runs, in execution order, and for each row

- the value of every variable **after** that line has finished, and
- **which line runs next**, chosen from a dropdown of the function's line
  numbers plus `return / end`.

The first row arrives pre-filled as a worked example, so the format is
demonstrated without giving anything away. A final box asks what the function
returns — the same question Step 2 used to ask on its own.

The table's rows, columns and answer key are all derived automatically by
executing the buggy code under Python's tracer (`sys.settrace`); task authors
supply only the sample input calls. The answer key never leaves the server,
and the student's submission is graded against a fresh capture.

**One attempt, and no feedback.** The student is told nothing about whether
they were right — not per cell, not the final output, not even a summary.
Revealing the trace would hand them the bug before Step 3 and turn Step 3 into
a measure of "can they use feedback" rather than "can they refute unaided."
Everything is scored server-side for later analysis.

**What this measures:** pure code-reading/tracing ability, on inputs the
researcher has already chosen — separate from the harder job of *inventing* a
distinguishing input in Step 3. Unlike a single output box, it says **where**
the student's mental execution left the machine's, and separates a
control-flow misconception.

**Why the change from output prediction.** Asking only for the return value
yields one bit per sample input. Both papers this design draws on reject that:
Nelson, Xie & Ko note that earlier comprehension-first pedagogies "lacked
assessment methods beyond I/O prediction, making it hard to give targeted
practice, diagnose misconceptions, and correct them", and instead hide values
in the machine state for the learner to fill in; Russell's generated multi-line
questions ask for "the control flow in the code and the changing values of
variables as execution progresses." A student can also produce the right output
for the wrong reason, which an output-only question cannot detect.

**Example:** the buggy implementation has a bug where the `elif` skips
checking `c` once `b` has already replaced `a`:

```python
1  def max_of_three(a, b, c):
2      largest = a
3      if b > largest:
4          largest = b
5      elif c > largest:      # bug: should be `if`, not `elif`
6          largest = c
7      return largest
```

For the sample input `max_of_three(2, 1, 3)` the student fills in:

| Step | Line executed | `a` | `b` | `c` | `largest` | Next line |
|---|---|---|---|---|---|---|
| 1 | `2: largest = a` | 2 | 1 | 3 | 2 | 3 | *(pre-filled)* |
| 2 | `3: if b > largest:` | ? | ? | ? | ? | ? |
| 3 | `5: elif c > largest:` | ? | ? | ? | ? | ? |
| 4 | `6: largest = c` | ? | ? | ? | ? | ? |
| 5 | `7: return largest` | ? | ? | ? | ? | — |

and then: what does `max_of_three(2, 1, 3)` return? `?`

Neither sample input exposes the bug — that's intentional; Step 2 is about
tracing skill, not about finding the flaw. The student moves on to Step 3
regardless of trace accuracy.

**What is scored, per sample input:**

| Measure | What it tells you |
|---|---|
| `value_cells_correct` / `_total` | accuracy at computing state |
| `next_line_correct` / `_total` | accuracy at control flow, scored separately |
| `first_divergence_step` | the exact step where their model left the machine's |
| `correct_at_buggy_line` | did they trace the buggy line — or the jump over it — correctly? |
| `final_output_correct` | the pre-redesign measure, kept for comparability |
| `right_answer_wrong_trace` | right output reached by a wrong route |

`correct_at_buggy_line` counts rows that execute a line the task author marked
as buggy **and** rows whose execution jumps over one — for `max_of_three`, the
`(1,2,3)` path never runs line 5, and the bug shows up precisely as the jump
from line 4 to line 7.

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

If a student instead submits `max_of_three(2,1,3)` again, both outputs
would be `3` — not a counter-example — and they'd be told to try a
different input.

## What gets measured, per step

For every step, the app logs a server timestamp the moment the step is
**shown** and another the moment the student **submits**, plus every
submission's content and correctness. This lets the analysis compute, per
student and per task:

- time spent forming I/O pairs (spec comprehension time)
- number of attempts needed to get all three I/O pairs right
- time spent tracing the buggy code (one attempt, so this is a clean
  single-interval measure), and the per-cell trace scores listed above
- time spent finding a counter-example, and how many attempts it took
- whether the *first* counter-example attempt succeeded (a proxy for how
  directly the student reasoned to it, versus trial-and-error)

Comparing these across students and across tasks is the core of the
difficulty analysis: e.g., a task where Step 1 is fast and correct but
Step 3 takes many attempts suggests the difficulty is in constructing a
distinguishing input, not in understanding the spec — whereas slow, error-
prone Step 1 attempts point to a specification the students didn't
understand well enough to reliably reason about the bug at all.

The Step 2 trace scores are what make that analysis decisive rather than
suggestive. A student who fails Step 3 with `correct_at_buggy_line` false
misread the code; one who fails it with a fully correct trace understood the
code and still could not construct a distinguishing input. Those are different
findings.