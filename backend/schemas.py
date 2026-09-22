from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class StartSessionRequest(BaseModel):
    student_identifier: str
    institute: str
    language: str  # "python" | "c" | "ocaml"
    # Optional explicit task — when omitted, picks the first Task for
    # `language` (lowest id), same as before. The frontend sends this
    # explicitly when advancing to the next task in a multi-task study run
    # (see App.jsx's handleNextTask) — the home page's initial "Start" still
    # omits it.
    task_id: Optional[int] = None


class StartSessionResponse(BaseModel):
    session_id: int
    task_id: int
    title: str
    language: str
    description: str
    function_signature: str
    # Echoed back so the frontend can start the NEXT task's session with the
    # same identity without having to separately thread student_identifier/
    # institute down from TaskIntro — this is the student's own submitted
    # data, already stored server-side per session, so echoing it back isn't
    # a new leak.
    student_identifier: str
    institute: str


class MarkShownRequest(BaseModel):
    session_id: int
    step: str  # one of StepName values


class IOPair(BaseModel):
    call: str       # e.g. "max_of_three(1, 2, 3)"
    expected: str   # e.g. "3"  (literal, parsed with ast.literal_eval)


class Step1SubmitRequest(BaseModel):
    session_id: int
    pairs: List[IOPair]  # expect exactly 3, validated server-side


class PairResult(BaseModel):
    """Full Step-1 result. Written to StepEvent.payload for analysis only —
    never returned to the student, because `actual` and `error` both carry
    information about the hidden reference implementation."""
    call: str
    expected: str
    actual: Optional[str] = None
    correct: bool
    error: Optional[str] = None


class PairResultPublic(BaseModel):
    """What the student sees after a Step-1 submission.

    Deliberately omits `actual`: revealing the reference implementation's
    output would let a student copy all three pairs back on the next attempt,
    which collapses the Step-1 gate and makes `attempt_number` meaningless —
    an attempt count of 2 could no longer be told apart from transcription.
    """
    call: str
    expected: str          # echo of what the student typed — their own input, no leak
    correct: bool
    could_not_run: bool = False   # the call errored; the wording lives in the UI


class TraceRow(BaseModel):
    """One row of the CONTROL-FLOW table — one row per PHYSICAL LINE of the
    function's source, not one per executed occurrence.

    Every line is listed regardless of whether it actually runs for this
    call, so the row list itself gives away nothing about which lines
    execute — that's the whole point (see trace_table.build_table).

    Asks ONLY how many times the line runs (`count`; a line can run any
    number of times under a loop, so this generalizes plain reachability —
    0 subsumes "no", any positive number subsumes "yes"). No variable
    values are asked here at all: that's the data-flow table's job, over a
    *different* sample input (see trace_table.py's module docstring for why
    the two are split and why that's safe). `count` is None unless the row
    is a pre-filled worked example (0 is a valid count to give — a line
    inside a branch that wasn't taken).

    Recursion isn't representable here: a line inside a recursive call would
    need one row per call depth (and per code path taken at each depth), not
    a flat per-line iteration count. Fine for the non-recursive CS1 tasks
    this was built for.
    """
    lineno: int
    line_text: str
    prefilled: bool = False
    count: Optional[int] = None   # None unless prefilled — the thing being asked


class TraceTable(BaseModel):
    call: str
    rows: List[TraceRow]
    truncated: bool = False
    error: Optional[str] = None           # set if the trace could not be captured


class DataFlowRow(BaseModel):
    """One row of a data-flow trace table — the TRUE execution skeleton is
    given outright (one row per actual occurrence, in execution order,
    exactly like the original pre-redesign table): `lineno`/`line_text`/
    `step` are never hidden. Only variable values are asked.

    Safe to reveal the skeleton here in a way it wasn't for the control-flow
    table: a data-flow table is always built for a DIFFERENT sample input
    than the ones used for the control-flow (count) question (see
    Task.trace_data_flow_inputs), so showing this input's execution path
    outright doesn't leak anything about the control-flow question's input.
    """
    step: int              # 1-based position in the true execution order
    lineno: int
    line_text: str
    prefilled: bool = False
    vars: Dict[str, Optional[str]]   # var name -> value if prefilled else None


class DataFlowTable(BaseModel):
    call: str
    var_names: List[str]
    rows: List[DataFlowRow]
    truncated: bool = False
    error: Optional[str] = None


class Step1SubmitResponse(BaseModel):
    all_correct: bool
    results: List[PairResultPublic]
    attempt_number: int
    # populated only when all_correct becomes True for the first time
    buggy_code: Optional[str] = None
    trace_sample_inputs: Optional[List[str]] = None
    trace_tables: Optional[List[TraceTable]] = None
    data_flow_tables: Optional[List[DataFlowTable]] = None
    # Set on EVERY response (correct or not) so the frontend knows whether to
    # ever offer the "show me examples" button, independent of this
    # particular attempt's outcome.
    examples_available: bool = False
    # Step 2's mutation-question config — rides on the same "Step 1 unlocked"
    # reveal as buggy_code/trace_tables, since it's shown alongside the buggy
    # code on Step 2. All three null = task has no mutation question.
    mutation_line_number: Optional[int] = None
    mutation_new_line_text: Optional[str] = None
    mutation_prompt: Optional[str] = None


class Step1ExamplesRequest(BaseModel):
    session_id: int


class Step1ExamplesResponse(BaseModel):
    # Reuses IOPair (call + expected) — `expected` here IS the real output of
    # task.correct_code for this author-curated call. Deliberately an oracle,
    # once, after a wrong attempt — see reveal_io_examples in main.py.
    examples: List[IOPair]


class TraceRowAnswer(BaseModel):
    lineno: int
    count: int = Field(ge=0)     # student's claimed number of times this line ran


class TraceAnswer(BaseModel):
    call: str
    rows: List[TraceRowAnswer]
    final_output: str      # preserves the pre-redesign measure for comparability


class DataFlowRowAnswer(BaseModel):
    step: int
    vars: Dict[str, str] = {}


class DataFlowAnswer(BaseModel):
    call: str
    rows: List[DataFlowRowAnswer]
    final_output: str


class Step2SubmitRequest(BaseModel):
    session_id: int
    traces: List[TraceAnswer]
    data_flow_traces: List[DataFlowAnswer] = []
    # Free-text answer to the Step 2 mutation-question panel (None/omitted
    # when the task has no mutation_prompt configured). Collect-only, like
    # everything else in Step 2 — no ground truth to grade free text
    # against, so this is never scored, just stored for later analysis.
    mutation_response: Optional[str] = None


class Step2SubmitResponse(BaseModel):
    """Deliberately opaque.

    Step 2 is collect-only: the student is told nothing about correctness, not
    per-cell, not the final output, not even a summary. Grading happens
    server-side into StepEvent.payload for later analysis. Adding any
    correctness field here would contaminate the Step 3 measurement.
    """
    accepted: bool
    attempt_number: int
    unlocked_counter_example: bool


class Step3SubmitRequest(BaseModel):
    session_id: int
    call: str  # the counter-example call, e.g. "max_of_three(5, 5, 5)"
    # The student's own predictions, made BEFORE either real output is
    # revealed — Step 3 used to just run both and show the results with no
    # prediction step at all, unlike Steps 1 and 2. Asking for these first
    # brings it in line: finding a valid counter-example input is only half
    # the reasoning: predicting the correct output tests spec comprehension
    # (like Step 1) and predicting the buggy output tests code tracing
    # (like Step 2), both anchored to the exact input the student chose.
    predicted_correct_output: str
    predicted_buggy_output: str


class Step3SubmitResponse(BaseModel):
    """
    Deliberately omits the real correct/buggy outputs. Step 3 allows
    unlimited resubmission (a student iterates toward a valid
    counter-example), so if every attempt revealed both real outputs, the
    step would become an oracle: try an input, read the two real values,
    try another — that's enough to reverse-engineer the bug's behavior
    across the input space without ever reasoning through the code, the
    same brute-force loophole Step 1 avoids by never revealing the
    reference implementation's output. Only RIGHT/WRONG is revealed per
    prediction — enough feedback to know whether their reasoning about each
    implementation was correct, not enough to read the answer off the
    response. The real values are still recorded server-side (StepEvent
    payload) for analysis.
    """
    call: str
    predicted_correct_output: str
    predicted_buggy_output: str
    correct_prediction_right: Optional[bool] = None
    buggy_prediction_right: Optional[bool] = None
    is_counter_example: bool
    # is_counter_example AND both predictions right. The only condition that
    # marks the session complete and shows the "task complete" banner — a
    # valid counter-example alone, with a wrong prediction, is told apart
    # from that and prompted to keep going. Computed server-side so the
    # frontend never has to re-derive it (and can't get it wrong).
    fully_successful: bool = False
    error: Optional[str] = None
    attempt_number: int


# ---------------------------------------------------------------------------
# Step 3 "your prior work" recap — echoes the student's OWN submitted answers
# from Steps 1 and 2 back to them, and nothing else. Every field below is
# hand-picked from the much richer stored StepEvent payloads (see
# main.py's get_my_work) — deliberately a narrower shape than what's stored,
# so a ground-truth/correctness field newly added to grade()'s output later
# can't silently start leaking through here.
# ---------------------------------------------------------------------------

class MyWorkIOPair(BaseModel):
    call: str
    expected: str


class MyWorkTraceRow(BaseModel):
    lineno: int
    line_text: str
    student_count: Optional[int] = None


class MyWorkControlFlowTrace(BaseModel):
    call: str
    rows: List[MyWorkTraceRow]
    student_final_output: Optional[str] = None


class MyWorkDataFlowRow(BaseModel):
    step: int
    lineno: int
    line_text: str
    vars: Dict[str, Optional[str]]   # the student's own submitted values only


class MyWorkDataFlowTrace(BaseModel):
    call: str
    rows: List[MyWorkDataFlowRow]
    student_final_output: Optional[str] = None


class Step3MyWorkRequest(BaseModel):
    session_id: int


class Step3MyWorkResponse(BaseModel):
    io_pairs: List[MyWorkIOPair]
    control_flow: List[MyWorkControlFlowTrace]
    data_flow: List[MyWorkDataFlowTrace]
    # From the TASK, not the stored payload — this is task-authored content
    # the student already saw during Step 2, not a secret.
    mutation_line_number: Optional[int] = None
    mutation_new_line_text: Optional[str] = None
    mutation_prompt: Optional[str] = None
    mutation_response: Optional[str] = None   # the student's own free text
