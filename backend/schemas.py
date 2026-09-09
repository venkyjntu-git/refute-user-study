from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class StartSessionRequest(BaseModel):
    student_identifier: str
    task_id: int


class StartSessionResponse(BaseModel):
    session_id: int
    task_id: int
    title: str
    description: str
    function_signature: str


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
    """One row of the blank trace table sent to the browser.

    Carries NO answers for cells the student must fill: `vars` values and
    `next_line` are None unless the row is a pre-filled worked example. The
    answer key stays on the server and is re-derived at grading time.
    """
    step: int
    lineno: int
    line_text: str
    depth: int = 0
    prefilled: bool = False
    vars: Dict[str, Optional[str]]        # var name -> value if prefilled else None
    next_line: Optional[str] = None       # prefilled rows only
    next_line_options: List[str]          # line numbers + "return / end"


class TraceTable(BaseModel):
    call: str
    var_names: List[str]                  # column order
    rows: List[TraceRow]
    truncated: bool = False
    error: Optional[str] = None           # set if the trace could not be captured


class Step1SubmitResponse(BaseModel):
    all_correct: bool
    results: List[PairResultPublic]
    attempt_number: int
    # populated only when all_correct becomes True for the first time
    buggy_code: Optional[str] = None
    trace_sample_inputs: Optional[List[str]] = None
    trace_tables: Optional[List[TraceTable]] = None


class TraceRowAnswer(BaseModel):
    step: int
    vars: Dict[str, str]
    next_line: Optional[str] = None


class TraceAnswer(BaseModel):
    call: str
    rows: List[TraceRowAnswer]
    final_output: str      # preserves the pre-redesign measure for comparability


class Step2SubmitRequest(BaseModel):
    session_id: int
    traces: List[TraceAnswer]


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


class Step3SubmitResponse(BaseModel):
    call: str
    correct_output: Optional[str] = None
    buggy_output: Optional[str] = None
    is_counter_example: bool
    error: Optional[str] = None
    attempt_number: int
