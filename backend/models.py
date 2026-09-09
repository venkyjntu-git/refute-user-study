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
