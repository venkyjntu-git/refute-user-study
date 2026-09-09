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
  4. counter_example     -> student submits one call; we run it against BOTH
                           correct and buggy code and report match/mismatch.

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
    task = db.query(models.Task).get(req.task_id)
    if not task:
        raise HTTPException(404, "task not found")

    session = models.StudySession(
        student_identifier=req.student_identifier,
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
    """Hand the student the buggy code and one blank trace table per sample input."""
    resp.buggy_code = task.buggy_code
    resp.trace_sample_inputs = task.trace_sample_inputs
    resp.trace_tables = [
        trace_table.build_table(task, call) for call in (task.trace_sample_inputs or [])
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

    # Ground truth is re-derived here, never taken from the request.
    graded = [trace_table.grade(task, answer) for answer in req.traces]
    summary = trace_table.summarise(graded)

    attempt_number = _next_attempt_number(db, session.id, models.StepName.buggy_trace)
    _log_event(
        db, session.id, models.StepName.buggy_trace, models.EventType.submitted,
        attempt_number=attempt_number,
        # is_correct stays the final-output measure so analysis written against
        # the pre-redesign data keeps working; the richer scores are in payload.
        is_correct=(summary.get("final_outputs_correct") == summary.get("traces_scored")
                    if summary.get("traces_scored") else None),
        payload={"traces": graded, "summary": summary},
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
            payload={"call": req.call, "error": err},
        )
        return schemas.Step3SubmitResponse(
            call=req.call, is_counter_example=False, error=err, attempt_number=attempt_number,
        )

    is_counter_example = correct_result.value_repr != buggy_result.value_repr
    # NOTE: for float-heavy tasks you may want a tolerance-based comparison
    # instead of strict repr() inequality.

    _log_event(
        db, session.id, models.StepName.counter_example, models.EventType.submitted,
        attempt_number=attempt_number, is_correct=is_counter_example,
        payload={
            "call": req.call,
            "correct_output": correct_result.value_repr,
            "buggy_output": buggy_result.value_repr,
        },
    )

    if is_counter_example:
        session.counter_example_completed = True
        db.commit()

    return schemas.Step3SubmitResponse(
        call=req.call,
        correct_output=correct_result.value_repr,
        buggy_output=buggy_result.value_repr,
        is_counter_example=is_counter_example,
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
        db.query(models.StepEvent, models.StudySession)
        .join(models.StudySession, models.StepEvent.session_id == models.StudySession.id)
        .order_by(models.StepEvent.session_id, models.StepEvent.timestamp)
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "session_id", "student_identifier", "task_id", "step", "event_type",
        "attempt_number", "is_correct", "timestamp", "payload_json",
    ])
    for ev, sess in rows:
        writer.writerow([
            sess.id, sess.student_identifier, sess.task_id, ev.step, ev.event_type,
            ev.attempt_number, ev.is_correct, ev.timestamp.isoformat(),
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
    Cell-level CSV of every step-2 trace answer — one row per
    (session, sample input, trace step, cell) — for the tracing analysis.

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
        "session_id", "student_identifier", "task_id", "timestamp", "call",
        "step", "lineno", "line_text", "depth", "cell_kind", "variable",
        "student_value", "actual_value", "correct", "prefilled",
        "first_divergence_step", "correct_at_buggy_line",
        "final_output_correct", "right_answer_wrong_trace",
    ])

    for ev, sess in rows:
        payload = ev.payload or {}
        for trace in payload.get("traces", []):
            if "error" in trace:
                continue
            common_tail = [
                trace.get("first_divergence_step"),
                trace.get("correct_at_buggy_line"),
                trace.get("final_output_correct"),
                trace.get("right_answer_wrong_trace"),
            ]
            for row in trace.get("rows", []):
                cells = [("variable", name, cell) for name, cell in row["cells"].items()]
                cells.append(("next_line", "", row["next_line"]))
                for kind, name, cell in cells:
                    writer.writerow([
                        sess.id, sess.student_identifier, sess.task_id,
                        ev.timestamp.isoformat(), trace.get("call"),
                        row["step"], row["lineno"], row["line_text"], row["depth"],
                        kind, name,
                        cell.get("student"), cell.get("actual"), cell.get("correct"),
                        cell.get("prefilled", False),
                    ] + common_tail)
            final = trace.get("final_output", {})
            writer.writerow([
                sess.id, sess.student_identifier, sess.task_id,
                ev.timestamp.isoformat(), trace.get("call"),
                "", "", "", "", "final_output", "",
                final.get("student"), final.get("actual"), final.get("correct"), False,
            ] + common_tail)

    buf.seek(0)
    return StreamingResponse(
        buf, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trace_cells.csv"},
    )


@app.get("/api/tasks")
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(models.Task).all()
    return [{"id": t.id, "title": t.title} for t in tasks]
