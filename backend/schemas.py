from typing import Optional, List, Any
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
    call: str
    expected: str
    actual: Optional[str] = None
    correct: bool
    error: Optional[str] = None


class Step1SubmitResponse(BaseModel):
    all_correct: bool
    results: List[PairResult]
    attempt_number: int
    # populated only when all_correct becomes True for the first time
    buggy_code: Optional[str] = None
    trace_sample_inputs: Optional[List[str]] = None


class TraceItem(BaseModel):
    call: str
    student_output: str


class Step2SubmitRequest(BaseModel):
    session_id: int
    traces: List[TraceItem]


class TraceResult(BaseModel):
    call: str
    student_output: str
    actual_buggy_output: Optional[str] = None
    matches_actual: Optional[bool] = None
    error: Optional[str] = None


class Step2SubmitResponse(BaseModel):
    results: List[TraceResult]
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
