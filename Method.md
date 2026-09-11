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
for the intended behavior. The function name and surrounding parentheses are
fixed in the UI — the student only fills in the arguments and the expected
output — so a call always has the right shape and name:

```
funcname(arguments)
expected output
```

Three pairs must use three different arguments; resubmitting the same call
(even reformatted, e.g. `f(1,2)` vs `f(1, 2)`) is rejected, so a single lucky
guess can't clear the gate on its own.

The system runs each of the student's calls against the **correct**
reference implementation (hidden from the student) and checks whether the
student's expected output matches. The student must get all three pairs
correct before moving on. Each pair is marked correct or incorrect and the
student may revise and resubmit as many times as they need — but **the
reference implementation's output is never shown**. If a call cannot be run at
all (wrong number of arguments, bad syntax, or a non-literal argument) the
student is told only to check the number and format of their arguments, not
the underlying Python error.

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

The student is now shown the **buggy implementation** for the first time.
This step can ask up to two separate questions, each over its *own* sample
input(s): **control flow** (does the student's model of which lines run
match the machine's) and, optionally, **data flow** (can the student
compute variable state, once control flow is no longer what's being
tested). They're kept separate deliberately — conflating them into one
combined per-line question can't tell you whether a wrong cell was a
control-flow misread or an arithmetic slip on a line the student correctly
identified as running.

#### Control flow

For each sample input in `trace_sample_inputs`, the student fills in a
table listing **every line of the function** — not just the ones that
actually run — and for each line says **how many times** that line runs for
this call (0 if it never does). Nothing else: no variable values are asked
here at all — that's the data-flow question's job, over a *different*
sample input (below). Splitting the two apart is deliberate: a wrong cell
in a combined question can't tell you whether the student mis-modeled
control flow or got control flow right and slipped computing a value,
whereas two clean scores can.

The table lists every line, reached or not, in source order — the row list
itself must never give away which lines execute. An earlier design listed
only executed lines, one row per occurrence, in execution order, with a
"what runs next" dropdown per row; it was replaced because that layout leaks
control flow for free: filling in row N, a student could just read row N+1's
"line executed" cell to get the "what's next" answer, or notice a line was
missing from the list entirely. Listing every physical line regardless of
outcome gives away nothing by presence or position — only a correctly
answered count does. A count of 0 subsumes a plain "no"; asking for a count
rather than yes/no is what lets a loop body be traced at all (it can run
more than once — the count is simply higher, with nothing new to build).

The first row(s) arrive pre-filled as a worked example (true count given
outright), so the format is demonstrated without giving anything away for
the rest of the table. A final box asks what the function returns — the
same question Step 2 used to ask on its own.

The table's rows and answer key are all derived automatically by executing
the buggy code under Python's tracer (`sys.settrace`); task authors supply
only the sample input calls. The answer key never leaves the server, and
the student's submission is graded against a fresh capture. Loops are
supported this way; recursion is not — a line inside a recursive call needs
one row per call depth (and potentially a different code path at each
depth), not a flat per-line count. Fine for the non-recursive CS1 tasks this
was built for, but a real constraint on what a future task can trace.

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

| Line | Code | Times? |
|---|---|---|
| 1 | `def max_of_three(a, b, c):` | 0 *(pre-filled)* |
| 2 | `largest = a` | ? |
| 3 | `if b > largest:` | ? |
| 4 | `largest = b` | ? |
| 5 | `elif c > largest:` | ? |
| 6 | `largest = c` | ? |
| 7 | `return largest` | ? |

and then: what does `max_of_three(2, 1, 3)` return? `?`

(Line 1 is the `def` line itself — it runs once when the function is
*defined*, not on each *call*, so the correct answer for this table is 0
times — an intentional first worked example, showing that "runs zero times"
is itself a valid, gradable answer. The true answers for the rest: lines 2,
3, 5, 6, 7 each run once; line 4 runs zero times — `b` (1) is never greater
than `largest` (2), so the `if` is false and, correctly, the `elif` is
checked instead. None of these lines loop, so every count here is 0 or 1;
see the README for how a loop body's count works.)

Neither sample input exposes the bug — that's intentional; Step 2 is about
tracing skill, not about finding the flaw. The student moves on to Step 3
regardless of trace accuracy.

**What is scored, per sample input:**

| Measure | What it tells you |
|---|---|
| `count_correct` / `_total` | accuracy at control flow — how many times each line runs, scored per line |
| `first_wrong_line` | the first line (source order) where their model left the machine's |
| `correct_at_buggy_line` | did they get the buggy line's count right? |
| `final_output_correct` | the pre-redesign measure, kept for comparability |
| `right_answer_wrong_trace` | right output reached by a wrong route |

`correct_at_buggy_line` checks the buggy line's count directly. For
`max_of_three`, the `(2,1,3)` path does run line 5 (the `elif`) once; a
student who thinks the `elif` never runs (mistaking it for another `if`)
gets this wrong. A loop-containing task exercises the same field
differently: undercounting or overcounting the buggy line's iterations
both fail it — a miscounted loop is still a control-flow miss.

#### Data flow (optional)

A task author can add a second, separate question via
`trace_data_flow_inputs`: sample input(s) *different* from every
control-flow input. For these, the table gives the true execution skeleton
outright — one row per line that actually runs, in execution order, exactly
like the very first design this measure had before the control-flow leak
was found and the table above was redesigned around it. The student isn't
asked which lines run or how many times; only the value of every variable
**after** each given line, plus the usual return-value box.

That reveal is only safe because control flow is never being tested for
*this* input — showing input B's execution path outright says nothing about
input A's, the one the control-flow question is still hiding. This is why
the two questions must use different inputs, and why they can sit on the
same page and be submitted together rather than needing a locked-in,
submit-then-reveal sequence: nothing about either question's input ever
depends on what the student answered for the other.

**What this isolates:** the control-flow table's `count_correct` and the
data-flow table's `value_cells_correct` are now two clean, non-overlapping
scores — one is purely "does their model of which lines run match the
machine's", the other is purely "can they compute state, given the path is
already known." A student who scores well on data-flow values but poorly on
control-flow counts has a control-flow misconception specifically, not a
general tracing weakness — useful for a task where you want to isolate which
half of "tracing" is actually the bottleneck, independent of whether the
student also had to figure out which lines ran. Before this split, a single
combined table couldn't tell those two failure modes apart from a wrong
cell alone.

**What is scored, per data-flow sample input:** `value_cells_correct` /
`_total` (accuracy at computing state, over every given true step),
`first_wrong_step` (the first true step, execution order, where a value
diverged), `correct_at_buggy_line`, `final_output_correct`,
`right_answer_wrong_trace` — the same shape as the old pre-split measure,
just without any count/reachability field, since there's nothing left to
guess about which lines ran.

---

### Step 3 — Find a counter-example (can they construct a distinguishing input?)

The task description and the buggy code (both already seen in Steps 1 and
2) are shown again here, so the student isn't relying on memory while
constructing the input. As in Steps 1 and 3's call boxes elsewhere, the
function name and parentheses are fixed — the student only types the
arguments.

The student supplies one input of their own choosing, and **before either
real output is revealed**, predicts both: what the *correct* code returns
for it, and what the *buggy* code (shown right above the input) returns for
it. The system runs the call against both implementations and reports,
per prediction, only whether it was **right or wrong** — never the real
value — plus the verdict: the input is a valid counter-example if and only
if the two *real* outputs differ (the predictions don't affect that
verdict, they're scored independently).

A valid input and two right predictions are three separate conditions, and
the session is only marked complete when all three hold — a valid
counter-example found alongside a wrong prediction is reported as partial
progress ("this input works, but recheck your reasoning"), not treated the
same as getting all three right. The point of the two predictions is to
verify the reasoning behind the input, not just the input itself; letting a
lucky (or iteratively narrowed-down) input count as full success would
undercut that.

The real outputs are withheld deliberately. Step 3 allows unlimited
resubmission, so if every attempt revealed both real values, the step would
become an oracle: try an input, read the two real outputs, try another —
enough to reverse-engineer the bug's behavior across the input space
without ever reasoning through the code, the same brute-force loophole
Step 1 avoids by never revealing the reference implementation's output for
a submitted pair. RIGHT/WRONG per prediction is real feedback (a student
without it couldn't calibrate their own reasoning across attempts at all),
but it's calibrated to leak far less than the value itself: a "WRONG" tells
them their guess wasn't the answer, not what the answer is.

This also closes a gap in the step's earlier design, which asked for no
prediction at all — the one place in the flow that didn't ask the student
to commit to an answer before seeing feedback. Asking for both predictions
here recombines what Steps 1 and 2 tested separately, now anchored to the
specific input the student chose to refute with: the correct-output
prediction is the same kind of question as Step 1 (do they know what the
function is supposed to do), and the buggy-output prediction is the same
kind as Step 2 (can they trace what the buggy code actually does) — except
now both are asked about the exact point in the input space the student
picked to make their case, rather than points the researcher chose for
them.

**What this measures:** the actual refutation skill — synthesizing an input
that exposes the discrepancy — plus, via the two predictions, whether the
student got there through correct reasoning about both implementations or
by trial and error (submit something, learn only right/wrong, adjust,
resubmit). Combining the correct mental model from Step 1 with an
understanding of the buggy code's actual behavior from Step 2 should mean a
student picks an input *and* predicts both outputs correctly on the same
attempt; a valid counter-example found alongside a wrong prediction
suggests some of that reasoning didn't actually happen — the right input
was found some other way (a lucky guess, or narrowing down across several
attempts using only the right/wrong signal, which is weaker feedback than
the old design gave but still enough to iterate on).

**Example:** the bug is triggered whenever `b` is *not* the largest but
does exceed `a`, so the `elif` branch checking `c` never runs, and the
true largest value (`c`) is missed. A student who reasons this through
might submit:

| Student submits | Predicted correct | Predicted buggy | Outcome |
|---|---|---|---|
| `max_of_three(1, 3, 5)` | `5` — RIGHT | `3` — RIGHT | ✅ fully successful — task complete |
| `max_of_three(1, 3, 5)` | `5` — RIGHT | `5` — WRONG | ⚠️ valid counter-example, but not fully successful — told to recheck their reasoning and try again |

If a student instead submits `max_of_three(2, 1, 3)` again, the real
outputs (both `3`) match — not a counter-example at all, regardless of
what they predicted — and they'd be told to try a different input, with
only their prediction accuracy shown, never the real values.

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
- whether the *first* attempt was `fully_successful` (valid input AND both
  predictions right) — the real proxy for how directly the student reasoned
  to it, versus trial-and-error
- three distinct per-attempt outcomes, not just pass/fail: `is_counter_example`
  (was the input valid), `correct_prediction_right` /
  `buggy_prediction_right` (was each prediction right), and
  `fully_successful` (all three at once — the only outcome that completes
  the session). A student can rack up several attempts that are valid
  counter-examples but not fully successful before getting one right on all
  three counts; comparing that count to their total attempts separates
  "found the right input but by trial and error" from "understood both
  implementations well enough to nail it in one"

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