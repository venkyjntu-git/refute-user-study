"""
ORM models.

StepEvent is the core timing artifact for the study: every time a step is
shown to the student, and every time they submit for that step, we write a
row with a server timestamp. Duration per attempt = submitted_at - shown_at
for the matching pair, computed in analysis, not stored redundantly.
"""
import enum
import datetime as dt

from sqlalchemy import (
    Column, Integer, String, Text, DateTime, ForeignKey, Boolean, Enum, JSON
)
from sqlalchemy.orm import relationship

from database import Base


class StepName(str, enum.Enum):
    task_description = "task_description"   # step 1 shown alongside task desc
    io_pairs = "io_pairs"                    # step 1: student gives 3 I/O pairs
    buggy_trace = "buggy_trace"               # step 3 (UI step 2): trace buggy code
    counter_example = "counter_example"       # step 4 (UI step 3): final refutation


class EventType(str, enum.Enum):
    shown = "shown"
    submitted = "submitted"


class Task(Base):
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)          # task description shown in step 1
    function_signature = Column(String, nullable=False)  # e.g. "def max_of_three(a, b, c):"
    correct_code = Column(Text, nullable=False)           # full correct function source
    buggy_code = Column(Text, nullable=False)             # full buggy function source
    # sample inputs shown to the student to trace in step 3 (UI step 2), as a JSON list
    # of call strings, e.g. ["max_of_three(1, 2, 3)", "max_of_three(-1, -5, -2)"]
    trace_sample_inputs = Column(JSON, nullable=False)

    # --- step 2 trace-table configuration (all optional; safe defaults) ---
    # Line number(s) within buggy_code that carry the bug, e.g. [5]. Used only
    # for analysis: it lets us score whether the student traced the buggy line
    # itself correctly, which is the metric that separates "misread the code"
    # from "read it fine but couldn't construct a counter-example". Null means
    # that metric is simply not computed for this task.
    buggy_line_numbers = Column(JSON, nullable=True)
    # How many leading rows arrive pre-filled as a worked example (scaffold
    # fading, cf. PLTutor). 1 demonstrates the format without giving anything
    # away; 0 asks for everything.
    trace_prefill_steps = Column(Integer, nullable=False, default=1, server_default="1")
    # When true, drop columns whose value is identical on every row of a trace
    # (typically parameters that are never reassigned). Those cells are visible
    # in the call itself and carry no tracing signal, but asking for them is a
    # uniform rule that leaks nothing, so this is off by default.
    trace_omit_unchanged_vars = Column(Boolean, nullable=False, default=False,
                                        server_default="0")

    sessions = relationship("StudySession", back_populates="task")


class StudySession(Base):
    __tablename__ = "study_sessions"

    id = Column(Integer, primary_key=True, index=True)
    student_identifier = Column(String, nullable=False, index=True)
    task_id = Column(Integer, ForeignKey("tasks.id"), nullable=False)
    created_at = Column(DateTime, default=dt.datetime.utcnow)

    # progression gates - which step the student has unlocked / completed
    io_pairs_completed = Column(Boolean, default=False)
    buggy_trace_completed = Column(Boolean, default=False)
    counter_example_completed = Column(Boolean, default=False)

    task = relationship("Task", back_populates="sessions")
    events = relationship("StepEvent", back_populates="session")


class StepEvent(Base):
    __tablename__ = "step_events"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("study_sessions.id"), nullable=False, index=True)
    step = Column(Enum(StepName), nullable=False)
    event_type = Column(Enum(EventType), nullable=False)
    timestamp = Column(DateTime, default=dt.datetime.utcnow, index=True)
    attempt_number = Column(Integer, default=1)  # increments on repeated 'submitted' for same step
    is_correct = Column(Boolean, nullable=True)  # null for 'shown' events / non-gated steps
    payload = Column(JSON, nullable=True)         # raw submission content + per-item results

    session = relationship("StudySession", back_populates="events")
