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
from sqlalchemy.exc import IntegrityError

from database import Base, engine, get_db
import analysis
import assignment
import auth
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

def _create_session(db: Session, task: models.Task, student_identifier: str,
                    institute: str, participant: models.Participant = None,
                    position: int = None) -> models.StudySession:
    session = models.StudySession(
        student_identifier=student_identifier,
        institute=institute,
        task_id=task.id,
        participant_id=participant.id if participant else None,
        position=position,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    _log_event(db, session.id, models.StepName.task_description, models.EventType.shown)
    # io_pairs step is shown immediately alongside the task description in this UI
    _log_event(db, session.id, models.StepName.io_pairs, models.EventType.shown)
    return session


def _session_response(session: models.StudySession) -> schemas.StartSessionResponse:
    task = session.task
    participant = session.participant
    # Only the participant's own language version of the code-mixed text.
    mixed = None
    if participant and task.description_mixed:
        mixed = task.description_mixed.get(participant.native_language) or None
    return schemas.StartSessionResponse(
        session_id=session.id,
        task_id=task.id,
        title=task.title,
        language=task.language,
        description=task.description,
        function_signature=task.function_signature,
        student_identifier=session.student_identifier,
        institute=session.institute,
        description_mixed=mixed,
        form=task.form,
        participant_id=session.participant_id,
        position=session.position,
        step3_max_attempts=task.step3_max_attempts,
        step3_attempts_used=sum(
            1 for e in session.events
            if e.step == models.StepName.counter_example
            and e.event_type == models.EventType.submitted
        ),
    )


@app.post("/api/session", response_model=schemas.StartSessionResponse)
def start_session(req: schemas.StartSessionRequest, db: Session = Depends(get_db)):
    if req.participant_id is not None:
        # Study run: start (or return) the participant's session for this
        # position, which must be the task their assignment gave them.
        participant = db.query(models.Participant).get(req.participant_id)
        if not participant:
            raise HTTPException(404, "participant not found")
        if req.position not in (1, 2):
            raise HTTPException(400, "position must be 1 or 2")
        assigned_id = participant.assigned_task_ids[req.position - 1]
        if req.task_id is not None and req.task_id != assigned_id:
            raise HTTPException(400, "task is not the one assigned for this position")
        existing = (
            db.query(models.StudySession)
            .filter_by(participant_id=participant.id, position=req.position)
            .first()
        )
        if existing:
            return _session_response(existing)
        task = db.query(models.Task).get(assigned_id)
        session = _create_session(db, task, participant.student_identifier,
                                  participant.institute, participant, req.position)
        return _session_response(session)

    if req.task_id is not None:
        # Explicit task — used when the frontend advances to the next task
        # in a multi-task study run (see App.jsx's handleNextTask).
        task = db.query(models.Task).get(req.task_id)
        if not task:
            raise HTTPException(404, "task not found")
        if task.language != req.language:
            raise HTTPException(400, f"task {req.task_id} is not a '{req.language}' task")
    else:
        # The home page picks a language, not a specific task: load the
        # first task authored for that language (lowest id) rather than
        # making the student/admin pick a task_id by hand. Study variants
        # are only reachable through a participant's assignment.
        task = (
            db.query(models.Task)
            .filter(models.Task.language == req.language, models.Task.variant_key.is_(None))
            .order_by(models.Task.id)
            .first()
        )
        if not task:
            raise HTTPException(404, f"no tasks available yet for language '{req.language}'")

    session = _create_session(db, task, req.student_identifier, req.institute)
    return _session_response(session)


# ---------------------------------------------------------------------------
# counterbalanced study: participant registration / resume
# ---------------------------------------------------------------------------

def _step3_attempts(db: Session, session_id: int) -> int:
    return _next_attempt_number(db, session_id, models.StepName.counter_example) - 1


def _task_closed(db: Session, session: models.StudySession) -> bool:
    """A study task is over once refuted or out of Step 3 attempts."""
    if session.counter_example_completed:
        return True
    limit = session.task.step3_max_attempts
    return bool(limit) and _step3_attempts(db, session.id) >= limit


def _stage_of(db: Session, session: models.StudySession) -> str:
    if _task_closed(db, session):
        return "done"
    if session.buggy_trace_completed:
        return "counter_example"
    if session.io_pairs_completed:
        return "trace"
    return "io_pairs"


def _assign_new_participant(db: Session, req: schemas.RegisterParticipantRequest):
    """Create the participant in the next slot at their institute. Returns
    (participant, resumed). Two simultaneous registrations at one institute
    collide on the unique (institute, slot) key; the loser retries with the
    next slot, so no two participants share a slot (and so a condition row
    within a block)."""
    task_ids = {
        t.variant_key: t.id
        for t in db.query(models.Task).filter(models.Task.variant_key.isnot(None))
    }
    for _ in range(10):
        slot = (
            db.query(func.count(models.Participant.id))
            .filter(models.Participant.institute == req.institute)
            .scalar()
        ) or 0
        row = assignment.condition_row_for_slot(req.institute, slot)
        keys = assignment.variants_for_row(row)
        missing = [k for k in keys if k not in task_ids]
        if missing:
            raise HTTPException(500, f"study tasks not seeded: {', '.join(missing)}")
        participant = models.Participant(
            student_identifier=req.student_identifier,
            institute=req.institute,
            native_language=req.native_language,
            schooling_medium=req.schooling_medium,
            english_proficiency=req.english_proficiency,
            slot=slot,
            condition_row=row,
            assigned_task_ids=[task_ids[k] for k in keys],
        )
        db.add(participant)
        try:
            db.commit()
            db.refresh(participant)
            return participant, False
        except IntegrityError:
            db.rollback()
            # Same student registering twice at once (a double click): the
            # identity key fired, so resume the row that won.
            existing = (
                db.query(models.Participant)
                .filter_by(institute=req.institute, student_identifier=req.student_identifier)
                .first()
            )
            if existing:
                return existing, True
    raise HTTPException(503, "could not assign a condition — please try again")


@app.post("/api/participant", response_model=schemas.RegisterParticipantResponse)
def register_participant(req: schemas.RegisterParticipantRequest, db: Session = Depends(get_db)):
    """
    Start or resume a participant in the counterbalanced study. A returning
    (institute, student_identifier) keeps the assignment — and the survey
    answers — from their first registration: a page refresh must never
    re-randomise anyone.
    """
    if not req.student_identifier.strip():
        raise HTTPException(400, "student identifier is required")
    participant = (
        db.query(models.Participant)
        .filter_by(institute=req.institute, student_identifier=req.student_identifier)
        .first()
    )
    resumed = participant is not None
    if not participant:
        participant, resumed = _assign_new_participant(db, req)

    session = (
        db.query(models.StudySession)
        .filter_by(participant_id=participant.id)
        .order_by(models.StudySession.position.desc())
        .first()
    )
    if session is None:
        first_task = db.query(models.Task).get(participant.assigned_task_ids[0])
        session = _create_session(db, first_task, participant.student_identifier,
                                  participant.institute, participant, 1)
    stage = _stage_of(db, session)
    if stage == "done" and session.position == 1:
        second_task = db.query(models.Task).get(participant.assigned_task_ids[1])
        session = _create_session(db, second_task, participant.student_identifier,
                                  participant.institute, participant, 2)
        stage = "io_pairs"

    return schemas.RegisterParticipantResponse(
        participant_id=participant.id,
        assigned_task_ids=participant.assigned_task_ids,
        resumed=resumed,
        session=_session_response(session),
        stage=stage,
    )


@app.post("/api/spec_view")
def log_spec_view(req: schemas.SpecViewRequest, db: Session = Depends(get_db)):
    """One row per spec version shown: the initial English view of a step,
    then every switch between English and the code-mixed version."""
    _get_session_or_404(db, req.session_id)
    if req.step not in ("io_pairs", "counter_example"):
        raise HTTPException(400, "invalid step")
    if req.version not in ("en", "mixed"):
        raise HTTPException(400, "invalid version")
    db.add(models.SpecViewEvent(
        session_id=req.session_id, step=req.step, version=req.version,
        timestamp=dt.datetime.utcnow(),
    ))
    db.commit()
    return {"ok": True}


@app.post("/api/step2/materials", response_model=schemas.StepMaterialsResponse)
def get_step_materials(req: schemas.StepMaterialsRequest, db: Session = Depends(get_db)):
    """Re-serve what Step 1 handed over on unlock, for a resumed session."""
    session = _get_session_or_404(db, req.session_id)
    if not session.io_pairs_completed:
        raise HTTPException(400, "complete the input/output pairs step first")
    resp = schemas.StepMaterialsResponse()
    _attach_trace_step(resp, session.task)
    return resp


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


def _attach_trace_step(resp, task: models.Task) -> None:
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

    # Step 2's mutation-question config rides on this same reveal — the
    # student needs it right when they first see the buggy code.
    resp.mutation_line_number = task.mutation_line_number
    resp.mutation_new_line_text = task.mutation_new_line_text
    resp.mutation_prompt = task.mutation_prompt


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

    # Once the student has requested the two worked examples (see
    # reveal_io_examples below), reusing one of those exact calls as their
    # own pair would trivially satisfy the gate without demonstrating
    # anything — permanently excluded for the rest of this session.
    if session.io_examples_shown:
        excluded = {sandbox.canonical_call(c) for c in (task.io_example_inputs or [])[:2]}
        reused = [p.call for p, cc in zip(req.pairs, canonical_calls) if cc in excluded]
        if reused:
            raise HTTPException(
                400,
                "please use a different input — you can't reuse a revealed "
                "example call: " + ", ".join(reused),
            )

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

    logged_pairs = [r.dict() for r in results]
    if task.variant_key:
        # Analysis only, never returned: would this pair already have refuted
        # the program the student is about to see, and is it a valid (under
        # the contextualized form, plausible) input for the task?
        for entry, pair in zip(logged_pairs, req.pairs):
            buggy = sandbox.run_call(task.buggy_code, pair.call)
            entry["buggy_actual"] = buggy.value_repr if buggy.ok else None
            entry["is_counterexample"] = (
                entry["actual"] is not None and buggy.ok
                and not sandbox.values_equal(entry["actual"], buggy.value_repr)
            )
            entry["invalid_reason"] = (
                sandbox.run_validator(task.input_validator, pair.call)
                if task.input_validator else None
            )

    _log_event(
        db, session.id, models.StepName.io_pairs, models.EventType.submitted,
        attempt_number=attempt_number, is_correct=all_correct,
        payload={"pairs": logged_pairs},
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
        examples_available=bool(task.io_example_inputs),
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


@app.post("/api/step1/examples", response_model=schemas.Step1ExamplesResponse)
def reveal_io_examples(req: schemas.Step1ExamplesRequest, db: Session = Depends(get_db)):
    """
    Unlocks after the student's first wrong Step 1 submission: reveals the
    task's two curated (call, correct-output) examples. This is a deliberate
    oracle — unlike the rest of the app, the real reference-implementation
    output IS shown here — but only for two author-chosen calls, only after
    a wrong attempt, and reusing either as one of the student's own pairs is
    then permanently excluded (see submit_io_pairs).
    """
    session = _get_session_or_404(db, req.session_id)
    task = session.task
    if not task.io_example_inputs:
        raise HTTPException(400, "no examples configured for this task")

    if not session.io_examples_shown:
        had_wrong_attempt = (
            db.query(models.StepEvent.id)
            .filter(
                models.StepEvent.session_id == session.id,
                models.StepEvent.step == models.StepName.io_pairs,
                models.StepEvent.event_type == models.EventType.submitted,
                models.StepEvent.is_correct.is_(False),
            )
            .first() is not None
        )
        if not had_wrong_attempt:
            raise HTTPException(400, "examples unlock only after an incorrect submission")
        session.io_examples_shown = True
        db.commit()
        _log_event(db, session.id, models.StepName.io_pairs, models.EventType.shown,
                    payload={"io_examples_revealed": True})
    # else: already shown earlier this session — idempotent re-fetch (e.g.
    # after a page refresh) just returns the same two examples again.

    examples = []
    for call in task.io_example_inputs[:2]:
        result = sandbox.run_call(task.correct_code, call)
        if result.ok:
            examples.append(schemas.IOPair(call=call, expected=result.value_repr))
        else:
            # Misconfigured task content, not a security issue — same
            # warn-don't-fail posture as _attach_trace_step's overlap check.
            print(f"WARNING: task {task.id} io_example_inputs call {call!r} "
                  f"could not run: {result.error}")
    return schemas.Step1ExamplesResponse(examples=examples)


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
            # Free text, collect-only — never graded (no ground truth to
            # check it against), None when the task has no mutation_prompt.
            "mutation_response": req.mutation_response,
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
# step 3 (UI): recap the student's own Step 1 + Step 2 work, then refute
# ---------------------------------------------------------------------------

@app.post("/api/step3/my_work", response_model=schemas.Step3MyWorkResponse)
def get_my_work(req: schemas.Step3MyWorkRequest, db: Session = Depends(get_db)):
    """
    Echoes the student's OWN submitted answers from Steps 1 and 2 back to
    them, and only those — every field returned here is explicitly
    allowlisted off the much richer stored StepEvent payloads (see the
    comments below), never passed through wholesale, specifically so this
    can never leak a ground-truth/correctness field. Step 2 is single-attempt
    zero-feedback; that has to hold here too, not just in the Step 2 response.
    """
    session = _get_session_or_404(db, req.session_id)
    if not session.buggy_trace_completed:
        raise HTTPException(400, "complete steps 1 and 2 first")
    task = session.task

    # Step 1: most recent CORRECT io_pairs submission — not "first correct",
    # since a student could keep experimenting with Step 1 after unlocking
    # it (nothing stops resubmission once io_pairs_completed is set), and we
    # want their latest winning set, not a stale one.
    io_event = (
        db.query(models.StepEvent)
        .filter(
            models.StepEvent.session_id == req.session_id,
            models.StepEvent.step == models.StepName.io_pairs,
            models.StepEvent.event_type == models.EventType.submitted,
            models.StepEvent.is_correct.is_(True),
        )
        .order_by(models.StepEvent.timestamp.desc())
        .first()
    )
    io_pairs = []
    if io_event and io_event.payload:
        for p in io_event.payload.get("pairs", []):
            # ALLOWLIST: call, expected (the student's own typed values).
            # NEVER: actual, error — both carry reference-implementation info.
            io_pairs.append(schemas.MyWorkIOPair(call=p["call"], expected=p["expected"]))

    # Step 2: the single buggy_trace submission (single-attempt gate above
    # already guarantees there's at most one).
    trace_event = (
        db.query(models.StepEvent)
        .filter(
            models.StepEvent.session_id == req.session_id,
            models.StepEvent.step == models.StepName.buggy_trace,
            models.StepEvent.event_type == models.EventType.submitted,
        )
        .order_by(models.StepEvent.timestamp.desc())
        .first()
    )
    control_flow, data_flow, mutation_response = [], [], None
    if trace_event and trace_event.payload:
        payload = trace_event.payload
        for trace in payload.get("traces", []):
            if "error" in trace:
                continue
            # ALLOWLIST per row: lineno, line_text, student_count.
            # NEVER: truth_count, count_correct — nor any trace-level field
            # (count_correct/count_total, first_wrong_line,
            # correct_at_buggy_line, final_output.actual/.correct,
            # final_output_correct, right_answer_wrong_trace,
            # trace_fully_correct) — every one of those is a
            # correctness/ground-truth signal Step 2 never reveals.
            control_flow.append(schemas.MyWorkControlFlowTrace(
                call=trace["call"],
                rows=[
                    schemas.MyWorkTraceRow(
                        lineno=r["lineno"], line_text=r["line_text"],
                        student_count=r["student_count"],
                    )
                    for r in trace.get("rows", [])
                ],
                student_final_output=trace.get("final_output", {}).get("student"),
            ))
        for trace in payload.get("data_flow_traces", []):
            if "error" in trace:
                continue
            # ALLOWLIST per cell: cell["student"] only.
            # NEVER: cell["actual"], cell["correct"], nor the trace-level
            # aggregates (same exclusion list as above, plus
            # value_cells_correct/value_cells_total).
            data_flow.append(schemas.MyWorkDataFlowTrace(
                call=trace["call"],
                rows=[
                    schemas.MyWorkDataFlowRow(
                        step=r["step"], lineno=r["lineno"], line_text=r["line_text"],
                        vars={name: cell.get("student") for name, cell in r["cells"].items()},
                    )
                    for r in trace.get("rows", [])
                ],
                student_final_output=trace.get("final_output", {}).get("student"),
            ))
        mutation_response = payload.get("mutation_response")

    return schemas.Step3MyWorkResponse(
        io_pairs=io_pairs, control_flow=control_flow, data_flow=data_flow,
        # From the TASK, not the stored payload — this is task-authored
        # content the student already saw during Step 2, not a secret.
        mutation_line_number=task.mutation_line_number,
        mutation_new_line_text=task.mutation_new_line_text,
        mutation_prompt=task.mutation_prompt,
        mutation_response=mutation_response,
    )


@app.post("/api/step3/submit", response_model=schemas.Step3SubmitResponse)
def submit_counter_example(req: schemas.Step3SubmitRequest, db: Session = Depends(get_db)):
    session = _get_session_or_404(db, req.session_id)
    if not session.buggy_trace_completed:
        raise HTTPException(400, "complete the trace step first")
    task = session.task
    if task.step3_max_attempts:
        raise HTTPException(400, "this task uses /api/step3/refute")

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


@app.post("/api/step3/refute", response_model=schemas.Step3RefuteResponse)
def submit_refutation(req: schemas.Step3RefuteRequest, db: Session = Depends(get_db)):
    """
    Study-mode Step 3: an input on which the program fails, plus the output
    the task requires for it and the output the program actually gives. A
    refutation succeeds when the input is valid for the task (and, under the
    contextualized form, plausible in the setting), the stated required
    output is right, the predicted program output is right, and the two
    differ. Each condition is logged separately for analysis.

    At most task.step3_max_attempts attempts. An input that cannot run at all
    (bad format) is rejected without using one up — that's a typing slip,
    not a refutation attempt. An invalid or implausible input does use one,
    and is the only failure whose reason the student is told.
    """
    session = _get_session_or_404(db, req.session_id)
    if not session.buggy_trace_completed:
        raise HTTPException(400, "complete the trace step first")
    task = session.task
    limit = task.step3_max_attempts
    if not limit:
        raise HTTPException(400, "this task uses /api/step3/submit")
    if _task_closed(db, session):
        raise HTTPException(400, "this problem is already finished")

    if sandbox._check_call_syntax(req.call, sandbox._function_names_from_code(task.correct_code)):
        raise HTTPException(400, sandbox.FORMAT_ERROR)
    invalid_reason = (
        sandbox.run_validator(task.input_validator, req.call) if task.input_validator else None
    )
    if invalid_reason == sandbox.FORMAT_ERROR:
        # Literal arguments, but the wrong number of them: still a typing slip.
        raise HTTPException(400, sandbox.FORMAT_ERROR)

    attempt_number = _step3_attempts(db, session.id) + 1
    payload = {
        "call": req.call, "required_output": req.required_output,
        "predicted_buggy_output": req.predicted_buggy_output,
        "how_found": req.how_found,
    }
    correct_result = buggy_result = None
    if invalid_reason is None:
        correct_result = sandbox.run_call(task.correct_code, req.call)
        buggy_result = sandbox.run_call(task.buggy_code, req.call)
        if not correct_result.ok:
            # The validator let through something the reference can't run —
            # a content gap in the validator; treat the input as invalid.
            invalid_reason = "This input is not valid for the task."
            payload["error"] = correct_result.error

    if invalid_reason is None:
        required_right = sandbox.values_equal(correct_result.value_repr, req.required_output)
        # A crash in the buggy program on a valid input is also a failure.
        program_differs = (not buggy_result.ok) or not sandbox.values_equal(
            correct_result.value_repr, buggy_result.value_repr)
        buggy_prediction_right = buggy_result.ok and sandbox.values_equal(
            buggy_result.value_repr, req.predicted_buggy_output)
        fully_successful = required_right and buggy_prediction_right and program_differs
        payload.update({
            "correct_output": correct_result.value_repr,
            "buggy_output": buggy_result.value_repr if buggy_result.ok else None,
            "buggy_error": buggy_result.error,
            "required_output_right": required_right,
            "buggy_prediction_right": buggy_prediction_right,
            "is_counter_example": program_differs,
        })
    else:
        fully_successful = False
    payload["invalid_reason"] = invalid_reason
    payload["fully_successful"] = fully_successful

    _log_event(
        db, session.id, models.StepName.counter_example, models.EventType.submitted,
        attempt_number=attempt_number, is_correct=fully_successful, payload=payload,
    )
    if fully_successful:
        session.counter_example_completed = True
        db.commit()

    attempts_remaining = max(0, limit - attempt_number)
    return schemas.Step3RefuteResponse(
        call=req.call,
        required_output=req.required_output,
        predicted_buggy_output=req.predicted_buggy_output,
        invalid_reason=invalid_reason,
        fully_successful=fully_successful,
        attempt_number=attempt_number,
        attempts_remaining=attempts_remaining,
        closed=fully_successful or attempts_remaining == 0,
    )


# ---------------------------------------------------------------------------
# admin / research export
# ---------------------------------------------------------------------------

@app.post("/api/admin/login", response_model=schemas.AdminLoginResponse)
def admin_login(req: schemas.AdminLoginRequest):
    if not auth.check_password(req.password):
        import time
        time.sleep(1)   # blunt brute-force throttle; one shared password
        raise HTTPException(401, "wrong password")
    return schemas.AdminLoginResponse(token=auth.issue_token(),
                                      expires_in=auth.TOKEN_TTL_SECONDS)


@app.get("/api/admin/analysis", dependencies=[Depends(auth.require_admin)])
def admin_analysis(institute: str = None, db: Session = Depends(get_db)):
    """Descriptive results along the paper's RQs — see analysis.py."""
    return analysis.analyse(db, institute or None)


@app.get("/api/admin/responses", dependencies=[Depends(auth.require_admin)])
def admin_responses(institute: str = None, db: Session = Depends(get_db)):
    """One row per study session (participant x problem) for the dashboard."""
    return analysis.session_rows(db, institute or None)


@app.get("/api/admin/institutes", dependencies=[Depends(auth.require_admin)])
def admin_institutes(db: Session = Depends(get_db)):
    rows = db.query(models.Participant.institute).distinct().all()
    return sorted(r[0] for r in rows)


@app.get("/api/admin/session_summary.csv", dependencies=[Depends(auth.require_admin)])
def export_session_summary_csv(institute: str = None, db: Session = Depends(get_db)):
    """The dashboard's per-session rows as a flat CSV — one row per
    participant x problem, ready for R/SPSS/pandas."""
    import io
    import csv
    from fastapi.responses import StreamingResponse

    rows = analysis.session_rows(db, institute or None)
    buf = io.StringIO()
    if rows:
        writer = csv.DictWriter(buf, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for r in rows:
            writer.writerow({k: (" | ".join(map(str, v)) if isinstance(v, list) else v)
                             for k, v in r.items()})
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=session_summary.csv"},
    )


@app.get("/api/admin/sessions/{session_id}/events", dependencies=[Depends(auth.require_admin)])
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


@app.get("/api/admin/export.csv", dependencies=[Depends(auth.require_admin)])
def export_csv(db: Session = Depends(get_db)):
    """
    Flat CSV of every event across all sessions — one row per event — for
    quick import into pandas/R/SPSS for the study analysis.
    """
    import io
    import csv
    from fastapi.responses import StreamingResponse

    rows = (
        db.query(models.StepEvent, models.StudySession, models.Task, models.Participant)
        .join(models.StudySession, models.StepEvent.session_id == models.StudySession.id)
        .join(models.Task, models.StudySession.task_id == models.Task.id)
        .outerjoin(models.Participant, models.StudySession.participant_id == models.Participant.id)
        .order_by(models.StepEvent.session_id, models.StepEvent.timestamp)
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "session_id", "student_identifier", "institute", "task_id", "language",
        # study design (blank for legacy sessions)
        "participant_id", "position", "condition_row", "variant_key", "problem_key",
        "form", "bug_kind", "native_language", "schooling_medium", "english_proficiency",
        "step", "event_type", "attempt_number", "is_correct", "timestamp", "payload_json",
    ])
    for ev, sess, task, part in rows:
        writer.writerow([
            sess.id, sess.student_identifier, sess.institute, sess.task_id, task.language,
            sess.participant_id, sess.position, part.condition_row if part else None,
            task.variant_key, task.problem_key, task.form, task.bug_kind,
            part.native_language if part else None, part.schooling_medium if part else None,
            part.english_proficiency if part else None,
            ev.step, ev.event_type, ev.attempt_number, ev.is_correct, ev.timestamp.isoformat(),
            __import__("json").dumps(ev.payload) if ev.payload else "",
        ])
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=study_export.csv"},
    )


@app.get("/api/admin/trace_export.csv", dependencies=[Depends(auth.require_admin)])
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


@app.get("/api/admin/data_flow_export.csv", dependencies=[Depends(auth.require_admin)])
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


@app.get("/api/admin/spec_view_export.csv", dependencies=[Depends(auth.require_admin)])
def export_spec_view_csv(db: Session = Depends(get_db)):
    """One row per spec view / English <-> code-mixed switch, with the study
    variant and participant survey alongside, for RQ3."""
    import io
    import csv
    from fastapi.responses import StreamingResponse

    rows = (
        db.query(models.SpecViewEvent, models.StudySession, models.Task, models.Participant)
        .join(models.StudySession, models.SpecViewEvent.session_id == models.StudySession.id)
        .join(models.Task, models.StudySession.task_id == models.Task.id)
        .outerjoin(models.Participant, models.StudySession.participant_id == models.Participant.id)
        .order_by(models.SpecViewEvent.session_id, models.SpecViewEvent.timestamp)
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "session_id", "participant_id", "student_identifier", "institute", "position",
        "variant_key", "problem_key", "form", "bug_kind",
        "native_language", "schooling_medium", "english_proficiency",
        "step", "version", "timestamp",
    ])
    for ev, sess, task, part in rows:
        writer.writerow([
            sess.id, sess.participant_id, sess.student_identifier, sess.institute, sess.position,
            task.variant_key, task.problem_key, task.form, task.bug_kind,
            part.native_language if part else None, part.schooling_medium if part else None,
            part.english_proficiency if part else None,
            ev.step, ev.version, ev.timestamp.isoformat(),
        ])
    buf.seek(0)
    return StreamingResponse(
        buf, media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=spec_views.csv"},
    )


@app.get("/api/tasks")
def list_tasks(db: Session = Depends(get_db)):
    # Legacy flow only: study variants are reached through an assignment.
    tasks = db.query(models.Task).filter(models.Task.variant_key.is_(None)).all()
    return [{"id": t.id, "title": t.title, "language": t.language} for t in tasks]


@app.get("/api/languages")
def list_languages(db: Session = Depends(get_db)):
    """Distinct languages that currently have at least one task — lets the
    home page (or an admin) tell which of the C/Python/OCaml options are
    actually loadable right now, without hardcoding that on the frontend."""
    rows = db.query(models.Task.language).distinct().all()
    return sorted(r[0] for r in rows)
