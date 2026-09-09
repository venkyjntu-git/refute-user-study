"""
Step 2 trace tables: building the blank skeleton and grading a submission.

Both directions run off the same ground truth — `sandbox.capture_trace` re-run
on the server — so the answer key never travels to the browser and a student
cannot submit their own key. Task authors supply only `trace_sample_inputs`;
the rows, columns and answers are all derived from executing the buggy code.

Why a table instead of "what does this return?": a single output box yields one
bit per sample input and cannot say WHERE the student's mental execution left
the machine's. The per-row scores below separate a control-flow misconception
(not noticing `elif` skips a branch) from an arithmetic slip, and localise both
relative to the buggy line — which is what tells us whether a Step 3 failure
was a comprehension failure or a counter-example-construction failure.
"""
from typing import Dict, List, Optional, Tuple

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


def _next_line_options(cap: sandbox.TraceCapture) -> List[str]:
    """Dropdown choices: every non-blank line of the function, plus 'return / end'."""
    options = [
        str(lineno) for lineno, text in (cap.code_lines or []) if text.strip()
    ]
    options.append(sandbox.NEXT_LINE_END)
    return options


def build_table(task, call: str) -> schemas.TraceTable:
    """Blank skeleton for one sample input, with every answer stripped out."""
    cap = sandbox.capture_trace(task.buggy_code, call)
    if not cap.ok:
        return schemas.TraceTable(call=call, var_names=[], rows=[], error=cap.error)

    var_names = _visible_var_names(cap, bool(task.trace_omit_unchanged_vars))
    options = _next_line_options(cap)
    prefill_steps = task.trace_prefill_steps if task.trace_prefill_steps is not None else 1

    rows = []
    for step in cap.steps:
        prefilled = step.step <= prefill_steps
        # Key present => cell is shown; value None => student must fill it.
        # Key absent => variable not in scope on this row; render as "—".
        cells: Dict[str, Optional[str]] = {}
        for name in var_names:
            if name not in step.vars_after:
                continue
            cells[name] = step.vars_after[name] if prefilled else None
        rows.append(schemas.TraceRow(
            step=step.step,
            lineno=step.lineno,
            line_text=step.line_text,
            depth=step.depth,
            prefilled=prefilled,
            vars=cells,
            next_line=step.next_line if prefilled else None,
            next_line_options=options,
        ))

    return schemas.TraceTable(
        call=call,
        var_names=var_names,
        rows=rows,
        truncated=cap.truncated,
    )


def _bug_adjacent_steps(cap: sandbox.TraceCapture, buggy_lines) -> List[int]:
    """
    Steps whose correctness depends on reading the buggy line right.

    That is not only rows that execute the buggy line — for `max_of_three(1,2,3)`
    the buggy `elif` never runs, and the bug shows up precisely as execution
    JUMPING OVER it. So a row also counts when the buggy line sits between the
    line it executed and the line that ran next, or when it is the next line.
    """
    if not buggy_lines:
        return []
    buggy = {int(n) for n in buggy_lines}
    steps = []
    for step in cap.steps:
        if step.lineno in buggy:
            steps.append(step.step)
            continue
        if step.next_line == sandbox.NEXT_LINE_END:
            nxt = None
        else:
            nxt = int(step.next_line)
        if nxt is not None and (nxt in buggy or any(step.lineno < b < nxt for b in buggy)):
            steps.append(step.step)
    return steps


def grade(task, answer: schemas.TraceAnswer) -> dict:
    """
    Score one submitted trace against a fresh capture. Returns the analysis
    record stored in StepEvent.payload — nothing here is sent to the student.
    """
    cap = sandbox.capture_trace(task.buggy_code, answer.call)
    if not cap.ok:
        return {"call": answer.call, "error": cap.error,
                "raw_submission": answer.dict()}

    var_names = _visible_var_names(cap, bool(task.trace_omit_unchanged_vars))
    prefill_steps = task.trace_prefill_steps if task.trace_prefill_steps is not None else 1
    submitted_by_step = {row.step: row for row in answer.rows}

    graded_rows = []
    value_correct = value_total = 0
    next_correct = next_total = 0
    divergence_steps = []

    for step in cap.steps:
        submitted = submitted_by_step.get(step.step)
        row_ok = True

        cells = {}
        for name in var_names:
            if name not in step.vars_after:
                continue          # not in scope on this row; never asked
            actual = step.vars_after[name]
            if step.step <= prefill_steps:
                cells[name] = {"prefilled": True, "actual": actual}
                continue
            student = (submitted.vars.get(name) if submitted else None)
            correct = student is not None and sandbox.values_equal(actual, student)
            cells[name] = {"student": student, "actual": actual, "correct": correct}
            value_total += 1
            value_correct += int(correct)
            row_ok = row_ok and correct

        if step.step <= prefill_steps:
            next_cell = {"prefilled": True, "actual": step.next_line}
        else:
            student_next = submitted.next_line if submitted else None
            next_ok = (student_next or "").strip() == step.next_line
            next_cell = {"student": student_next, "actual": step.next_line,
                         "correct": next_ok}
            next_total += 1
            next_correct += int(next_ok)
            row_ok = row_ok and next_ok

        if not row_ok:
            divergence_steps.append(step.step)

        graded_rows.append({
            "step": step.step,
            "lineno": step.lineno,
            "line_text": step.line_text,
            "depth": step.depth,
            "cells": cells,
            "next_line": next_cell,
        })

    final_actual = cap.return_repr
    final_correct = sandbox.values_equal(final_actual, answer.final_output or "")

    bug_steps = _bug_adjacent_steps(cap, task.buggy_line_numbers)
    graded_by_step = {r["step"]: r for r in graded_rows}

    def _row_all_correct(step_no: int) -> bool:
        row = graded_by_step[step_no]
        cell_ok = all(c.get("correct", True) for c in row["cells"].values())
        return cell_ok and row["next_line"].get("correct", True)

    correct_at_buggy_line = (
        all(_row_all_correct(s) for s in bug_steps) if bug_steps else None
    )

    trace_has_errors = bool(divergence_steps)
    return {
        "call": answer.call,
        "truncated": cap.truncated,
        "rows": graded_rows,
        "final_output": {"student": answer.final_output, "actual": final_actual,
                         "correct": final_correct},
        # --- per-trace metrics for analysis ---
        "value_cells_correct": value_correct,
        "value_cells_total": value_total,
        "next_line_correct": next_correct,
        "next_line_total": next_total,
        "first_divergence_step": divergence_steps[0] if divergence_steps else None,
        "bug_adjacent_steps": bug_steps,
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
        "value_cells_correct": _total("value_cells_correct"),
        "value_cells_total": _total("value_cells_total"),
        "next_line_correct": _total("next_line_correct"),
        "next_line_total": _total("next_line_total"),
        "traces_fully_correct": sum(g["trace_fully_correct"] for g in scored),
        "final_outputs_correct": sum(g["final_output_correct"] for g in scored),
        "any_right_answer_wrong_trace": any(g["right_answer_wrong_trace"] for g in scored),
        "correct_at_buggy_line": (all(at_buggy) if at_buggy else None),
    }
