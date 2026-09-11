"""
FastAPI backend for the Refute-problem user study.

Flow enforced server-side (see models.StepName):
  1. task_description  -> shown when session starts
  2. io_pairs           -> student submits 3 (call, expected) pairs, checked
                           against the CORRECT code. Must all be correct to
                           unlock the next step.
  3. buggy_trace         -> student is shown the buggy code plus, for each
                           sample input, a blank execution trace table (one row
                           per executed line: the variable values that line
                           produced, and which line runs next). Collect-only
                           and single-attempt: the student is told nothing
                           about correctness, because revealing the trace would
                           hand them the bug before step 4. Grading happens
                           server-side into StepEvent.payload.
  4. counter_example     -> student submits one call PLUS a prediction of
                           what each of the correct and buggy code returns
                           for it; we run both, report the real outputs and
                           whether each prediction was right, and report
                           match/mismatch (a valid counter-example needs the
                           two real outputs to differ, regardless of the
                           predictions).

Every step logs a 'shown' event (call /api/event when the UI renders the
step) and every submission logs a 'submitted' event with a payload and
timestamp, so elapsed-time-per-step can be computed as
submitted.timestamp - shown.timestamp (most recent 'shown' before that
submission).
"""
from typing import List
import datetime as dt
import os

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import Base, engine, get_db
import models
import schemas
import sandbox
import trace_table

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Refute Problem Study API")

# ALLOWED_ORIGINS is a comma-separated list of frontend origins, e.g.
# "https://refute-study.onrender.com". Unset (local dev) falls back to "*".
# Note: the browser rejects allow_credentials with a "*" origin, so the two
# branches differ deliberately — the app uses no cookies either way.
_origins = [o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "").split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins or ["*"],
    allow_credentials=bool(_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health():
    """Liveness probe for Render — deliberately does not touch the database."""
    return {"status": "ok"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _get_session_or_404(db: Session, session_id: int) -> models.StudySession:
    sess = db.query(models.StudySession).get(session_id)
    if not sess:
        raise HTTPException(404, "session not found")
    return sess


def _log_event(db: Session, session_id: int, step: models.StepName,
                event_type: models.EventType, attempt_number: int = 1,
                is_correct=None, payload=None):
    ev = models.StepEvent(
        session_id=session_id,
        step=step,
        event_type=event_type,
        attempt_number=attempt_number,
        is_correct=is_correct,
        payload=payload,
        timestamp=dt.datetime.utcnow(),
    )
    db.add(ev)
    db.commit()
    return ev


def _next_attempt_number(db: Session, session_id: int, step: models.StepName) -> int:
    count = (
        db.query(func.count(models.StepEvent.id))
        .filter(
            models.StepEvent.session_id == session_id,
            models.StepEvent.step == step,
            models.StepEvent.event_type == models.EventType.submitted,
        )
        .scalar()
    )
    return (count or 0) + 1


# ---------------------------------------------------------------------------
# session lifecycle
# ---------------------------------------------------------------------------

@app.post("/api/session", response_model=schemas.StartSessionResponse)
def start_session(req: schemas.StartSessionRequest, db: Session = Depends(get_db)):
    # The home page picks a language, not a specific task: load the first
    # task authored for that language (lowest id) rather than making the
    # student/admin pick a task_id by hand.
    task = (
        db.query(models.Task)
        .filter(models.Task.language == req.language)
        .order_by(models.Task.id)
        .first()
    )
    if not task:
        raise HTTPException(404, f"no tasks available yet for language '{req.language}'")

    session = models.StudySession(
        student_identifier=req.student_identifier,
        institute=req.institute,
        task_id=task.id,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    _log_event(db, session.id, models.StepName.task_description, models.EventType.shown)
    # io_pairs step is shown immediately alongside the task description in this UI
    _log_event(db, session.id, models.StepName.io_pairs, models.EventType.shown)

    return schemas.StartSessionResponse(
        session_id=session.id,
        task_id=task.id,
        title=task.title,
        language=task.language,
        description=task.description,
        function_signature=task.function_signature,
    )


@app.post("/api/event")
def mark_shown(req: schemas.MarkShownRequest, db: Session = Depends(get_db)):
    """Frontend calls this the moment a step is rendered, for accurate timing."""
    _get_session_or_404(db, req.session_id)
    try:
        step = models.StepName(req.step)
    except ValueError:
        raise HTTPException(400, "invalid step name")
    _log_event(db, req.session_id, step, models.EventType.shown)
    return {"ok": True}


def _attach_trace_step(resp: schemas.Step1SubmitResponse, task: models.Task) -> None:
    """Hand the student the buggy code, one control-flow trace table per
    trace_sample_inputs call, and one data-flow trace table per
    trace_data_flow_inputs call (if the task has any — optional, additive)."""
    resp.buggy_code = task.buggy_code
    resp.trace_sample_inputs = task.trace_sample_inputs
    resp.trace_tables = [
        trace_table.build_table(task, call) for call in (task.trace_sample_inputs or [])
    ]

    # A data-flow table reveals its call's true execution path outright —
    # only safe because it's a DIFFERENT call from every control-flow input.
    # A task author who accidentally reuses one defeats the control-flow
    # question for that specific call; this can't be validated at task
    # creation (tasks are inserted directly, no admin API), so catch it here
    # instead. Warn, don't fail the request — a misconfigured task shouldn't
    # break Step 1 for a student over what is a content bug, not a security one.
    cf_canonical = {sandbox.canonical_call(c) for c in (task.trace_sample_inputs or [])}
    df_canonical = {sandbox.canonical_call(c) for c in (task.trace_data_flow_inputs or [])}
    overlap = cf_canonical & df_canonical
    if overlap:
        print(f"WARNING: task {task.id} ({task.title!r}) reuses call(s) {overlap} in both "
              f"trace_sample_inputs and trace_data_flow_inputs — the data-flow table will "
              f"reveal that call's execution path, defeating the control-flow question for it.")

    resp.data_flow_tables = [
        trace_table.build_data_flow_table(task, call)
        for call in (task.trace_data_flow_inputs or [])
    ]


# ---------------------------------------------------------------------------
# step 1: three I/O pairs, checked against correct code
# ---------------------------------------------------------------------------

@app.post("/api/step1/submit", response_model=schemas.Step1SubmitResponse)
def submit_io_pairs(req: schemas.Step1SubmitRequest, db: Session = Depends(get_db)):
    session = _get_session_or_404(db, req.session_id)
    task = session.task

    if len(req.pairs) != 3:
        raise HTTPException(400, "exactly 3 input/output pairs are required")

    # The point of asking for three pairs is to probe three different points
    # in the input space; the same call three times (or the same call
    # reformatted, e.g. "f(1,2,3)" vs "f(1, 2, 3)") would let a student clear
    # the gate off one lucky guess. Compare canonical forms, not raw strings.
    canonical_calls = [sandbox.canonical_call(p.call) for p in req.pairs]
    if len(set(canonical_calls)) < len(canonical_calls):
        raise HTTPException(400, "please use three different calls — at least two of your pairs use the same input")

    results: List[schemas.PairResult] = []
    for pair in req.pairs:
        exec_result = sandbox.run_call(task.correct_code, pair.call)
        if not exec_result.ok:
            results.append(schemas.PairResult(
                call=pair.call, expected=pair.expected, correct=False, error=exec_result.error
            ))
            continue
        correct = sandbox.values_equal(exec_result.value_repr, pair.expected)
        results.append(schemas.PairResult(
            call=pair.call, expected=pair.expected,
            actual=exec_result.value_repr, correct=correct,
        ))

    all_correct = all(r.correct for r in results)
    attempt_number = _next_attempt_number(db, session.id, models.StepName.io_pairs)

    _log_event(
        db, session.id, models.StepName.io_pairs, models.EventType.submitted,
        attempt_number=attempt_number, is_correct=all_correct,
        payload={"pairs": [r.dict() for r in results]},
    )

    # The student is told which pairs are wrong, never what the right answer was:
    # handing back the reference output lets them copy all three on the next
    # attempt, which turns the gate into a formality. The full results (with
    # `actual` and the real error text) stay in the logged payload above.
    public_results = [
        schemas.PairResultPublic(
            call=r.call, expected=r.expected,
            correct=r.correct, could_not_run=r.error is not None,
        )
        for r in results
    ]

    resp = schemas.Step1SubmitResponse(
        all_correct=all_correct, results=public_results, attempt_number=attempt_number,
    )

    if all_correct and not session.io_pairs_completed:
        session.io_pairs_completed = True
        db.commit()
        _attach_trace_step(resp, task)
        _log_event(db, session.id, models.StepName.buggy_trace, models.EventType.shown)
    elif session.io_pairs_completed:
        # already unlocked previously; still return the buggy code so a page
        # refresh doesn't strand the student
        _attach_trace_step(resp, task)

    return resp


# ---------------------------------------------------------------------------
# step 2 (UI): fill in the execution trace of the buggy code
# ---------------------------------------------------------------------------

@app.post("/api/step2/submit", response_model=schemas.Step2SubmitResponse)
def submit_trace(req: schemas.Step2SubmitRequest, db: Session = Depends(get_db)):
    session = _get_session_or_404(db, req.session_id)
    if not session.io_pairs_completed:
        raise HTTPException(400, "complete the input/output pairs step first")
    # Single attempt by design: with no feedback there is nothing to learn from
    # a resubmission, and allowing one would muddy the step-2 timing measure.
    if session.buggy_trace_completed:
        raise HTTPException(400, "trace step already submitted")
    task = session.task

    # Ground truth is re-derived here, never taken from the request. The
    # control-flow question (req.traces) and the data-flow question
    # (req.data_flow_traces, optional — empty for a task with no
    # trace_data_flow_inputs) are graded independently, since they measure
    # different things over different sample inputs.
    graded = [trace_table.grade(task, answer) for answer in req.traces]
    summary = trace_table.summarise(graded)
    data_flow_graded = [trace_table.grade_data_flow(task, answer) for answer in req.data_flow_traces]
    data_flow_summary = trace_table.summarise_data_flow(data_flow_graded)

    total_scored = summary.get("traces_scored", 0) + data_flow_summary.get("traces_scored", 0)
    total_final_correct = (summary.get("final_outputs_correct", 0)
                            + data_flow_summary.get("final_outputs_correct", 0))

    attempt_number = _next_attempt_number(db, session.id, models.StepName.buggy_trace)
    _log_event(
        db, session.id, models.StepName.buggy_trace, models.EventType.submitted,
        attempt_number=attempt_number,
        # is_correct stays the final-output measure so analysis written against
        # the pre-redesign data keeps working; the richer scores are in payload.
        is_correct=(total_final_correct == total_scored if total_scored else None),
        payload={
            "traces": graded, "summary": summary,
            "data_flow_traces": data_flow_graded, "data_flow_summary": data_flow_summary,
        },
    )

    session.buggy_trace_completed = True
    db.commit()
    _log_event(db, session.id, models.StepName.counter_example, models.EventType.shown)

    # Nothing about correctness crosses back to the student.
    return schemas.Step2SubmitResponse(
        accepted=True, attempt_number=attempt_number, unlocked_counter_example=True,
    )


# ---------------------------------------------------------------------------
# step 3 (UI): submit the counter-example itself
# ---------------------------------------------------------------------------

@app.post("/api/step3/submit", response_model=schemas.Step3SubmitResponse)
def submit_counter_example(req: schemas.Step3SubmitRequest, db: Session = Depends(get_db)):
    session = _get_session_or_404(db, req.session_id)
    if not session.buggy_trace_completed:
        raise HTTPException(400, "complete the trace step first")
    task = session.task

    correct_result = sandbox.run_call(task.correct_code, req.call)
    buggy_result = sandbox.run_call(task.buggy_code, req.call)

    attempt_number = _next_attempt_number(db, session.id, models.StepName.counter_example)

    if not correct_result.ok or not buggy_result.ok:
        err = correct_result.error or buggy_result.error
        _log_event(
            db, session.id, models.StepName.counter_example, models.EventType.submitted,
            attempt_number=attempt_number, is_correct=False,
            payload={
                "call": req.call, "error": err,
                "predicted_correct_output": req.predicted_correct_output,
                "predicted_buggy_output": req.predicted_buggy_output,
            },
        )
        return schemas.Step3SubmitResponse(
            call=req.call,
            predicted_correct_output=req.predicted_correct_output,
            predicted_buggy_output=req.predicted_buggy_output,
            is_counter_example=False, error=err, attempt_number=attempt_number,
        )

    is_counter_example = correct_result.value_repr != buggy_result.value_repr
    # NOTE: for float-heavy tasks you may want a tolerance-based comparison
    # instead of strict repr() inequality.
    correct_prediction_right = sandbox.values_equal(
        correct_result.value_repr, req.predicted_correct_output
    )
    buggy_prediction_right = sandbox.values_equal(
        buggy_result.value_repr, req.predicted_buggy_output
    )
    # "Fully successful" requires all three: a genuinely differing input AND
    # both predictions right. A valid counter-example found on the back of a
    # wrong prediction means some of the reasoning didn't actually happen
    # (a lucky guess, or narrowing down via the right/wrong signal alone) —
    # that shouldn't read as task-complete the same way getting all three
    # right does.
    fully_successful = is_counter_example and correct_prediction_right and buggy_prediction_right

    _log_event(
        db, session.id, models.StepName.counter_example, models.EventType.submitted,
        attempt_number=attempt_number, is_correct=fully_successful,
        payload={
            "call": req.call,
            "predicted_correct_output": req.predicted_correct_output,
            "predicted_buggy_output": req.predicted_buggy_output,
            "correct_output": correct_result.value_repr,
            "buggy_output": buggy_result.value_repr,
            "correct_prediction_right": correct_prediction_right,
            "buggy_prediction_right": buggy_prediction_right,
            "is_counter_example": is_counter_example,
            "fully_successful": fully_successful,
        },
    )

    if fully_successful:
        session.counter_example_completed = True
        db.commit()

    # correct_result.value_repr / buggy_result.value_repr are deliberately
    # NOT returned to the student — see Step3SubmitResponse's docstring.
    # They're already in the StepEvent payload above for analysis.
    return schemas.Step3SubmitResponse(
        call=req.call,
        predicted_correct_output=req.predicted_correct_output,
        predicted_buggy_output=req.predicted_buggy_output,
        correct_prediction_right=correct_prediction_right,
        buggy_prediction_right=buggy_prediction_right,
        is_counter_example=is_counter_example,
        fully_successful=fully_successful,
        attempt_number=attempt_number,
    )


# ---------------------------------------------------------------------------
# admin / research export
# ---------------------------------------------------------------------------

@app.get("/api/admin/sessions/{session_id}/events")
def get_session_events(session_id: int, db: Session = Depends(get_db)):
    session = _get_session_or_404(db, session_id)
    events = (
        db.query(models.StepEvent)
        .filter(models.StepEvent.session_id == session_id)
        .order_by(models.StepEvent.timestamp)
        .all()
    )
    return [
        {
            "step": e.step, "event_type": e.event_type, "timestamp": e.timestamp.isoformat(),
            "attempt_number": e.attempt_number, "is_correct": e.is_correct, "payload": e.payload,
        }
        for e in events
    ]


@app.get("/api/admin/export.csv")
def export_csv(db: Session = Depends(get_db)):
    """
    Flat CSV of every event across all sessions — one row per event — for
    quick import into pandas/R/SPSS for the study analysis.
    """
    import io
    import csv
    from fastapi.responses import StreamingResponse

    rows = (
        db.query(models.StepEvent, models.StudySession, models.Task)
        .join(models.StudySession, models.StepEvent.session_id == models.StudySession.id)
        .join(models.Task, models.StudySession.task_id == models.Task.id)
        .order_by(models.StepEvent.session_id, models.StepEvent.timestamp)
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "session_id", "student_identifier", "institute", "task_id", "language",
        "step", "event_type", "attempt_number", "is_correct", "timestamp", "payload_json",
    ])
    for ev, sess, task in rows:
        writer.writerow([
            sess.id, sess.student_identifier, sess.institute, sess.task_id, task.language,
            ev.step, ev.event_type, ev.attempt_number, ev.is_correct, ev.timestamp.isoformat(),
            __import__("json").dumps(ev.payload) if ev.payload else "",
        ])
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=study_export.csv"},
    )


@app.get("/api/admin/trace_export.csv")
def export_trace_csv(db: Session = Depends(get_db)):
    """
    Cell-level CSV of every step-2 CONTROL-FLOW answer — one row per
    (session, sample input, source line) — for the tracing analysis. Each
    line asks only a count (how many times it runs), so there's exactly one
    row per line here, no iteration/variable dimension at all (see
    data_flow_export.csv for the values side of Step 2).

    The general export dumps `payload` as an opaque JSON blob, which is fine
    for the other steps but unusable for per-cell stats in pandas/R/SPSS.
    """
    import io
    import csv
    from fastapi.responses import StreamingResponse

    rows = (
        db.query(models.StepEvent, models.StudySession)
        .join(models.StudySession, models.StepEvent.session_id == models.StudySession.id)
        .filter(
            models.StepEvent.step == models.StepName.buggy_trace,
            models.StepEvent.event_type == models.EventType.submitted,
        )
        .order_by(models.StepEvent.session_id, models.StepEvent.timestamp)
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "session_id", "student_identifier", "institute", "task_id", "timestamp", "call",
        "lineno", "line_text", "cell_kind",
        "student_value", "actual_value", "correct",
        "first_wrong_line", "correct_at_buggy_line",
        "final_output_correct", "right_answer_wrong_trace",
    ])

    for ev, sess in rows:
        payload = ev.payload or {}
        for trace in payload.get("traces", []):
            if "error" in trace:
                continue
            common_tail = [
                trace.get("first_wrong_line"),
                trace.get("correct_at_buggy_line"),
                trace.get("final_output_correct"),
                trace.get("right_answer_wrong_trace"),
            ]
            for row in trace.get("rows", []):
                writer.writerow([
                    sess.id, sess.student_identifier, sess.institute, sess.task_id,
                    ev.timestamp.isoformat(), trace.get("call"),
                    row["lineno"], row["line_text"], "count",
                    row["student_count"], row["truth_count"], row["count_correct"],
                ] + common_tail)
            final = trace.get("final_output", {})
            writer.writerow([
                sess.id, sess.student_identifier, sess.institute, sess.task_id,
                ev.timestamp.isoformat(), trace.get("call"),
                "", "", "final_output",
                final.get("student"), final.get("actual"), final.get("correct"),
            ] + common_tail)

    buf.seek(0)
    return StreamingResponse(
        buf, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trace_cells.csv"},
    )


@app.get("/api/admin/data_flow_export.csv")
def export_data_flow_csv(db: Session = Depends(get_db)):
    """
    Cell-level CSV of every step-2 DATA-FLOW answer — one row per
    (session, sample input, true execution step, variable). Separate from
    trace_export.csv because the shapes genuinely differ: a data-flow row
    is keyed by the true execution `step` (given outright, nothing to guess),
    with no count/iteration/reachability concept at all.
    """
    import io
    import csv
    from fastapi.responses import StreamingResponse

    rows = (
        db.query(models.StepEvent, models.StudySession)
        .join(models.StudySession, models.StepEvent.session_id == models.StudySession.id)
        .filter(
            models.StepEvent.step == models.StepName.buggy_trace,
            models.StepEvent.event_type == models.EventType.submitted,
        )
        .order_by(models.StepEvent.session_id, models.StepEvent.timestamp)
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "session_id", "student_identifier", "institute", "task_id", "timestamp", "call",
        "step", "lineno", "line_text", "cell_kind", "variable",
        "student_value", "actual_value", "correct",
        "first_wrong_step", "correct_at_buggy_line",
        "final_output_correct", "right_answer_wrong_trace",
    ])

    for ev, sess in rows:
        payload = ev.payload or {}
        for trace in payload.get("data_flow_traces", []):
            if "error" in trace:
                continue
            common_tail = [
                trace.get("first_wrong_step"),
                trace.get("correct_at_buggy_line"),
                trace.get("final_output_correct"),
                trace.get("right_answer_wrong_trace"),
            ]
            for row in trace.get("rows", []):
                for name, cell in row["cells"].items():
                    writer.writerow([
                        sess.id, sess.student_identifier, sess.institute, sess.task_id,
                        ev.timestamp.isoformat(), trace.get("call"),
                        row["step"], row["lineno"], row["line_text"], "variable", name,
                        cell.get("student"), cell.get("actual"), cell.get("correct"),
                    ] + common_tail)
            final = trace.get("final_output", {})
            writer.writerow([
                sess.id, sess.student_identifier, sess.institute, sess.task_id,
                ev.timestamp.isoformat(), trace.get("call"),
                "", "", "", "final_output", "",
                final.get("student"), final.get("actual"), final.get("correct"),
            ] + common_tail)

    buf.seek(0)
    return StreamingResponse(
        buf, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=data_flow_cells.csv"},
    )


@app.get("/api/tasks")
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(models.Task).all()
    return [{"id": t.id, "title": t.title, "language": t.language} for t in tasks]


@app.get("/api/languages")
def list_languages(db: Session = Depends(get_db)):
    """Distinct languages that currently have at least one task — lets the
    home page (or an admin) tell which of the C/Python/OCaml options are
    actually loadable right now, without hardcoding that on the frontend."""
    rows = db.query(models.Task.language).distinct().all()
    return sorted(r[0] for r in rows)
