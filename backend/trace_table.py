"""
Step 2 trace tables: building the blank skeleton and grading a submission.

Both directions run off the same ground truth — `sandbox.capture_trace` re-run
on the server — so the answer key never travels to the browser and a student
cannot submit their own key. Task authors supply only sample-input calls; the
rows, columns and answers are all derived from executing the buggy code.

Step 2 asks two SEPARATE questions, cleanly split by what they test:

- CONTROL FLOW (`build_table` / `grade` below, `Task.trace_sample_inputs`):
  one row per PHYSICAL LINE of the function, not one per executed
  occurrence — every line listed regardless of whether it actually runs, so
  the row list itself gives away nothing about which lines execute. Each
  non-prefilled row asks ONLY "how many times does this run?" (`count`; a
  line can run any number of times under a loop, so this generalizes plain
  reachability — 0 subsumes "no", any positive number subsumes "yes"). NO
  variable values are asked here.

  An earlier design listed only executed lines, one row per occurrence, in
  execution order, with a "what runs next" dropdown per row; it leaked
  control flow for free (row N+1 always told you row N's answer, or a
  missing line told you it never ran). Listing every physical line
  regardless of outcome closes that. A later version of this same table
  also asked for variable values per line, with the student's own claimed
  count driving how many value-entry rows appeared (never the true count,
  to avoid the same class of leak) — that's been split out entirely into
  the data-flow question below, so control flow now measures only "does
  the student's model of which lines run match the machine's", uncontaminated
  by whether they can also compute state. Recursion is NOT handled: a line
  inside a recursive call needs one row per call depth (and per code path
  taken at each depth), not a flat per-line count. Out of scope.

- DATA FLOW (`build_data_flow_table` / `grade_data_flow` below,
  `Task.trace_data_flow_inputs`): asks only for variable values, with the
  true execution skeleton given outright — one row per actual occurrence,
  in execution order, exactly like the very first design this file had
  before the control-flow leak was found. That reveal is safe here
  specifically because a data-flow table is always built for a DIFFERENT
  sample input than the control-flow question's — showing input B's
  execution path outright says nothing about input A's, so there is no
  leak to guard against, and no need for count/iteration machinery at all.

The two questions can sit on the same page and be submitted together
because they never share an input, and together they separate a
control-flow misconception (not noticing `elif` skips a branch, or
miscounting a loop) from a pure arithmetic slip — which is what tells us
whether a Step 3 failure was a comprehension failure or a
counter-example-construction failure.
"""
from typing import Dict, List, Optional

import sandbox
import schemas


def _visible_var_names(cap: sandbox.TraceCapture, omit_unchanged: bool) -> List[str]:
    """Column order for the table, optionally dropping never-mutated variables."""
    names = list(cap.var_names or [])
    if not omit_unchanged:
        return names
    # A variable that holds one value on every row it exists in (and exists on
    # every row) carries no tracing signal — it is readable straight off the
    # call. Anything that appears part-way through stays, since when it comes
    # into scope is itself a thing to trace.
    kept = []
    for name in names:
        seen = {step.vars_after.get(name) for step in cap.steps}
        if len(seen) > 1:
            kept.append(name)
    return kept


def _iterations_by_line(cap: sandbox.TraceCapture) -> Dict[int, List[dict]]:
    """
    Ground truth per physical line: an ORDERED list of `vars_after` dicts,
    one per time that line actually executed during this call (cap.steps is
    already in execution/occurrence order). A line missing from this dict —
    or present with an empty list — never ran; len(...) is the true count.

    Replaces an earlier version that kept only the first occurrence per
    line, which was fine for straight-line/branching code (every line runs
    at most once) but silently discarded every iteration after the first
    for a loop body — exactly the case the count-based design below exists
    to handle.
    """
    iterations: Dict[int, List[dict]] = {}
    for step in cap.steps:
        iterations.setdefault(step.lineno, []).append(step.vars_after)
    return iterations


def _prefilled_linenos(cap: sandbox.TraceCapture, prefill_steps: int) -> set:
    """
    The worked-example rows: the first `prefill_steps` rows of the table as
    displayed (source order) — not the first N *executed* steps. The table's
    literal first row must be the one that's given, or "the first row is
    filled in for you" stops matching what's on screen. Those aren't always
    the same line: a function's first physical line can be one that never
    executes on a call at all (e.g. `def f(...):` itself only runs once, at
    definition time — see build_table's handling of a zero-count prefilled
    row), so anchoring to execution order could prefill a row that isn't
    even the one the student sees first.
    """
    non_blank = [lineno for lineno, text in (cap.code_lines or []) if text.strip()]
    return set(non_blank[:prefill_steps])


def build_table(task, call: str) -> schemas.TraceTable:
    """Blank skeleton for one control-flow sample input: every physical line,
    with its true count stripped out except on prefilled rows."""
    cap = sandbox.capture_trace(task.buggy_code, call)
    if not cap.ok:
        return schemas.TraceTable(call=call, rows=[], error=cap.error)

    prefill_steps = task.trace_prefill_steps if task.trace_prefill_steps is not None else 1
    iterations_by_line = _iterations_by_line(cap)
    prefilled_linenos = _prefilled_linenos(cap, prefill_steps)

    rows = []
    for lineno, text in (cap.code_lines or []):
        if not text.strip():
            continue  # skip blank lines
        true_count = len(iterations_by_line.get(lineno, []))
        if lineno in prefilled_linenos:
            # A count of 0 (e.g. a `def` line, or a branch not taken) is
            # itself a valid, informative example to show.
            rows.append(schemas.TraceRow(
                lineno=lineno, line_text=text, prefilled=True, count=true_count,
            ))
        else:
            rows.append(schemas.TraceRow(
                lineno=lineno, line_text=text, prefilled=False, count=None,
            ))

    return schemas.TraceTable(call=call, rows=rows, truncated=cap.truncated)


def grade(task, answer: schemas.TraceAnswer) -> dict:
    """
    Score one submitted control-flow trace against a fresh capture. Returns
    the analysis record stored in StepEvent.payload — nothing here is sent
    to the student. Purely a count comparison per line — no variable values
    are asked or graded here at all (see grade_data_flow for that).
    """
    cap = sandbox.capture_trace(task.buggy_code, answer.call)
    if not cap.ok:
        return {"call": answer.call, "error": cap.error,
                "raw_submission": answer.dict()}

    prefill_steps = task.trace_prefill_steps if task.trace_prefill_steps is not None else 1
    iterations_by_line = _iterations_by_line(cap)
    prefilled_linenos = _prefilled_linenos(cap, prefill_steps)
    submitted_by_line = {row.lineno: row for row in answer.rows}

    graded_rows = []
    count_correct = count_total = 0
    wrong_linenos = []

    for lineno, text in (cap.code_lines or []):
        if not text.strip():
            continue
        if lineno in prefilled_linenos:
            continue  # given, not graded

        true_count = len(iterations_by_line.get(lineno, []))
        submitted = submitted_by_line.get(lineno)
        student_count = submitted.count if submitted else None
        count_ok = student_count is not None and student_count == true_count
        count_total += 1
        count_correct += int(count_ok)
        if not count_ok:
            wrong_linenos.append(lineno)

        graded_rows.append({
            "lineno": lineno,
            "line_text": text,
            "truth_count": true_count,
            "student_count": student_count,
            "count_correct": count_ok,
        })

    final_actual = cap.return_repr
    final_correct = sandbox.values_equal(final_actual, answer.final_output or "")

    buggy_lines = {int(n) for n in (task.buggy_line_numbers or [])}
    buggy_rows = [r for r in graded_rows if r["lineno"] in buggy_lines]
    correct_at_buggy_line = (
        all(r["count_correct"] for r in buggy_rows) if buggy_rows else None
    )

    trace_has_errors = bool(wrong_linenos)
    return {
        "call": answer.call,
        "truncated": cap.truncated,
        "rows": graded_rows,
        "final_output": {"student": answer.final_output, "actual": final_actual,
                         "correct": final_correct},
        # --- per-trace metrics for analysis ---
        "count_correct": count_correct,
        "count_total": count_total,
        # First physical line (source order) whose count diverged from the
        # truth. Analogous to the old first_divergence_step, but over line
        # number rather than execution order now that rows aren't
        # execution-ordered.
        "first_wrong_line": wrong_linenos[0] if wrong_linenos else None,
        "correct_at_buggy_line": correct_at_buggy_line,
        "final_output_correct": final_correct,
        # Right answer via a wrong route — the trial-and-error signal Edwards
        # (cited by Russell) warns output-only assessment cannot detect.
        "right_answer_wrong_trace": final_correct and trace_has_errors,
        "trace_fully_correct": not trace_has_errors,
    }


def summarise(graded: List[dict]) -> dict:
    """Aggregate across the sample inputs, for the flat CSV export."""
    scored = [g for g in graded if "error" not in g]
    if not scored:
        return {"traces_scored": 0}

    def _total(key):
        return sum(g[key] for g in scored)

    at_buggy = [g["correct_at_buggy_line"] for g in scored
                if g["correct_at_buggy_line"] is not None]
    return {
        "traces_scored": len(scored),
        "count_correct": _total("count_correct"),
        "count_total": _total("count_total"),
        "traces_fully_correct": sum(g["trace_fully_correct"] for g in scored),
        "final_outputs_correct": sum(g["final_output_correct"] for g in scored),
        "any_right_answer_wrong_trace": any(g["right_answer_wrong_trace"] for g in scored),
        "correct_at_buggy_line": (all(at_buggy) if at_buggy else None),
    }


# ---------------------------------------------------------------------------
# Data-flow question: full trace given, values only (see module docstring)
# ---------------------------------------------------------------------------

def build_data_flow_table(task, call: str) -> schemas.DataFlowTable:
    """
    Blank skeleton for a data-flow sample input: the true execution
    skeleton — one row per actual occurrence, in execution order — is
    included outright (lineno/line_text/step are never None). Only `vars`
    values are stripped for non-prefilled rows.
    """
    cap = sandbox.capture_trace(task.buggy_code, call)
    if not cap.ok:
        return schemas.DataFlowTable(call=call, var_names=[], rows=[], error=cap.error)

    var_names = _visible_var_names(cap, bool(task.trace_omit_unchanged_vars))
    prefill_steps = task.trace_prefill_steps if task.trace_prefill_steps is not None else 1

    rows = []
    for step in cap.steps:
        prefilled = step.step <= prefill_steps
        cells: Dict[str, Optional[str]] = {}
        for name in var_names:
            if name not in step.vars_after:
                continue
            cells[name] = step.vars_after[name] if prefilled else None
        rows.append(schemas.DataFlowRow(
            step=step.step, lineno=step.lineno, line_text=step.line_text,
            prefilled=prefilled, vars=cells,
        ))

    return schemas.DataFlowTable(
        call=call, var_names=var_names, rows=rows, truncated=cap.truncated,
    )


def grade_data_flow(task, answer: schemas.DataFlowAnswer) -> dict:
    """
    Score one data-flow submission. Much simpler than grade() above: the
    execution order is given, not asked, so there's no count/reachability to
    get wrong — every non-prefilled true step is graded on its values alone,
    matched by `step` (already the true position, not a student claim).
    """
    cap = sandbox.capture_trace(task.buggy_code, answer.call)
    if not cap.ok:
        return {"call": answer.call, "error": cap.error, "raw_submission": answer.dict()}

    var_names = _visible_var_names(cap, bool(task.trace_omit_unchanged_vars))
    prefill_steps = task.trace_prefill_steps if task.trace_prefill_steps is not None else 1
    submitted_by_step = {row.step: row for row in answer.rows}

    graded_rows = []
    value_correct = value_total = 0
    wrong_steps = []

    for step in cap.steps:
        if step.step <= prefill_steps:
            continue  # given, not graded

        submitted = submitted_by_step.get(step.step)
        cells = {}
        row_ok = True
        for name in var_names:
            if name not in step.vars_after:
                continue  # not in scope at this point; never graded
            actual = step.vars_after[name]
            student_val = submitted.vars.get(name) if submitted else None
            correct = student_val is not None and sandbox.values_equal(actual, student_val)
            cells[name] = {"student": student_val, "actual": actual, "correct": correct}
            value_total += 1
            value_correct += int(correct)
            row_ok = row_ok and correct

        if not row_ok:
            wrong_steps.append(step.step)

        graded_rows.append({
            "step": step.step, "lineno": step.lineno, "line_text": step.line_text,
            "cells": cells,
        })

    final_actual = cap.return_repr
    final_correct = sandbox.values_equal(final_actual, answer.final_output or "")

    buggy_lines = {int(n) for n in (task.buggy_line_numbers or [])}
    buggy_rows = [r for r in graded_rows if r["lineno"] in buggy_lines]
    correct_at_buggy_line = (
        all(all(c.get("correct", True) for c in r["cells"].values()) for r in buggy_rows)
        if buggy_rows else None
    )

    trace_has_errors = bool(wrong_steps)
    return {
        "call": answer.call,
        "truncated": cap.truncated,
        "rows": graded_rows,
        "final_output": {"student": answer.final_output, "actual": final_actual,
                         "correct": final_correct},
        "value_cells_correct": value_correct,
        "value_cells_total": value_total,
        "first_wrong_step": wrong_steps[0] if wrong_steps else None,
        "correct_at_buggy_line": correct_at_buggy_line,
        "final_output_correct": final_correct,
        "right_answer_wrong_trace": final_correct and trace_has_errors,
        "trace_fully_correct": not trace_has_errors,
    }


def summarise_data_flow(graded: List[dict]) -> dict:
    """Aggregate across data-flow sample inputs, for the flat CSV export."""
    scored = [g for g in graded if "error" not in g]
    if not scored:
        return {"traces_scored": 0}

    def _total(key):
        return sum(g[key] for g in scored)

    at_buggy = [g["correct_at_buggy_line"] for g in scored
                if g["correct_at_buggy_line"] is not None]
    return {
        "traces_scored": len(scored),
        "value_cells_correct": _total("value_cells_correct"),
        "value_cells_total": _total("value_cells_total"),
        "traces_fully_correct": sum(g["trace_fully_correct"] for g in scored),
        "final_outputs_correct": sum(g["final_output_correct"] for g in scored),
        "any_right_answer_wrong_trace": any(g["right_answer_wrong_trace"] for g in scored),
        "correct_at_buggy_line": (all(at_buggy) if at_buggy else None),
    }
