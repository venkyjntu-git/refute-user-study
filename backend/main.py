"""
FastAPI backend for the Refute-problem user study.

Flow enforced server-side (see models.StepName):
  1. task_description  -> shown when session starts
  2. io_pairs           -> student submits 3 (call, expected) pairs, checked
                           against the CORRECT code. Must all be correct to
                           unlock the next step.
  3. buggy_trace         -> student is shown buggy code + 2 sample inputs and
                           traces the output by hand. Not gated (this is the
                           learning task itself), but we score it against the
                           actual buggy-code output for analysis.
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

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import func

from database import Base, engine, get_db
import models
import schemas
import sandbox

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Refute Problem Study API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your frontend origin(s) before real deployment
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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

    resp = schemas.Step1SubmitResponse(
        all_correct=all_correct, results=results, attempt_number=attempt_number,
    )

    if all_correct and not session.io_pairs_completed:
        session.io_pairs_completed = True
        db.commit()
        resp.buggy_code = task.buggy_code
        resp.trace_sample_inputs = task.trace_sample_inputs
        _log_event(db, session.id, models.StepName.buggy_trace, models.EventType.shown)
    elif session.io_pairs_completed:
        # already unlocked previously; still return the buggy code so a page
        # refresh doesn't strand the student
        resp.buggy_code = task.buggy_code
        resp.trace_sample_inputs = task.trace_sample_inputs

    return resp


# ---------------------------------------------------------------------------
# step 2 (UI): trace buggy code on sample inputs
# ---------------------------------------------------------------------------

@app.post("/api/step2/submit", response_model=schemas.Step2SubmitResponse)
def submit_trace(req: schemas.Step2SubmitRequest, db: Session = Depends(get_db)):
    session = _get_session_or_404(db, req.session_id)
    if not session.io_pairs_completed:
        raise HTTPException(400, "complete the input/output pairs step first")
    task = session.task

    results: List[schemas.TraceResult] = []
    for item in req.traces:
        exec_result = sandbox.run_call(task.buggy_code, item.call)
        if not exec_result.ok:
            results.append(schemas.TraceResult(
                call=item.call, student_output=item.student_output, error=exec_result.error
            ))
            continue
        matches = sandbox.values_equal(exec_result.value_repr, item.student_output)
        results.append(schemas.TraceResult(
            call=item.call, student_output=item.student_output,
            actual_buggy_output=exec_result.value_repr, matches_actual=matches,
        ))

    attempt_number = _next_attempt_number(db, session.id, models.StepName.buggy_trace)
    _log_event(
        db, session.id, models.StepName.buggy_trace, models.EventType.submitted,
        attempt_number=attempt_number,
        payload={"traces": [r.dict() for r in results]},
    )

    if not session.buggy_trace_completed:
        session.buggy_trace_completed = True
        db.commit()
        _log_event(db, session.id, models.StepName.counter_example, models.EventType.shown)

    return schemas.Step2SubmitResponse(
        results=results, attempt_number=attempt_number, unlocked_counter_example=True,
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


@app.get("/api/tasks")
def list_tasks(db: Session = Depends(get_db)):
    tasks = db.query(models.Task).all()
    return [{"id": t.id, "title": t.title} for t in tasks]
