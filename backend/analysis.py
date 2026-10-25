"""
Descriptive analysis of the counterbalanced study, following the paper's
research questions:

  RQ1  With the code held fixed, how does the form of the specification
       affect correctness and time?
  RQ2  Does this effect differ between context-independent (buggy1) and
       context-sensitive (buggy2) bugs?
  RQ3  How often, when, and for which students and forms is the code-mixed
       version used?

plus the step-wise diagnostics the three-step design exists for: was a
failed refutation a task-comprehension failure (Step 1), a code-tracing
failure (Step 2), or neither?

Everything is computed from the raw event log on request — nothing here is
stored — and only study sessions (those with a participant) are included.
These are descriptive counts for the dashboard, not inferential statistics;
the CSV exports are the input for the real analysis.
"""
import statistics
from collections import defaultdict
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

import models

FORMS = ("direct", "contextualized")
BUGS = ("buggy1", "buggy2")
BUG_LABEL = {"buggy1": "Buggy1 (context-independent)", "buggy2": "Buggy2 (context-sensitive)"}
PROFICIENCY_BANDS = (("low (1-2)", (1, 2)), ("mid (3)", (3,)), ("high (4-5)", (4, 5)))


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------

def _rate(rows: List[dict], pred) -> dict:
    """{"k", "n", "pct"} for the rows satisfying pred, out of rows."""
    n = len(rows)
    k = sum(1 for r in rows if pred(r))
    return {"k": k, "n": n, "pct": round(100 * k / n, 1) if n else None}


def _median(values) -> Optional[float]:
    values = [v for v in values if v is not None]
    return round(statistics.median(values), 1) if values else None


def _mean(values) -> Optional[float]:
    values = [v for v in values if v is not None]
    return round(statistics.mean(values), 2) if values else None


def _seconds(start, end) -> Optional[float]:
    if start is None or end is None:
        return None
    return round((end - start).total_seconds(), 1)


def _band(proficiency: Optional[int]) -> Optional[str]:
    for name, values in PROFICIENCY_BANDS:
        if proficiency in values:
            return name
    return None


# ---------------------------------------------------------------------------
# one row per study session
# ---------------------------------------------------------------------------

def session_rows(db: Session, institute: Optional[str] = None) -> List[dict]:
    q = (
        db.query(models.StudySession, models.Participant, models.Task)
        .join(models.Participant, models.StudySession.participant_id == models.Participant.id)
        .join(models.Task, models.StudySession.task_id == models.Task.id)
    )
    if institute:
        q = q.filter(models.Participant.institute == institute)
    triples = q.order_by(models.StudySession.id).all()
    if not triples:
        return []
    ids = [s.id for s, _, _ in triples]

    events = defaultdict(list)
    for ev in (db.query(models.StepEvent).filter(models.StepEvent.session_id.in_(ids))
               .order_by(models.StepEvent.timestamp)):
        events[ev.session_id].append(ev)
    views = defaultdict(list)
    for v in (db.query(models.SpecViewEvent).filter(models.SpecViewEvent.session_id.in_(ids))
              .order_by(models.SpecViewEvent.timestamp)):
        views[v.session_id].append(v)

    return [_session_row(s, p, t, events[s.id], views[s.id]) for s, p, t in triples]


def _session_row(sess, part, task, evs, views) -> dict:
    def of(step, kind):
        return [e for e in evs if e.step == step and e.event_type == kind]

    S, E = models.StepName, models.EventType

    # Step 1 — task comprehension
    s1_shown = of(S.io_pairs, E.shown)
    s1_subs = of(S.io_pairs, E.submitted)
    s1_first_ok = next((e for e in s1_subs if e.is_correct), None)
    pairs = [p for e in s1_subs for p in ((e.payload or {}).get("pairs") or [])]

    # Step 2 — code tracing (single attempt)
    s2_shown = of(S.buggy_trace, E.shown)
    s2_sub = (of(S.buggy_trace, E.submitted) or [None])[0]
    s2 = (s2_sub.payload or {}) if s2_sub else {}
    cf, df = s2.get("summary") or {}, s2.get("data_flow_summary") or {}
    cells_ok = (cf.get("count_correct") or 0) + (df.get("value_cells_correct") or 0)
    cells_all = (cf.get("count_total") or 0) + (df.get("value_cells_total") or 0)
    scored = (cf.get("traces_scored") or 0) + (df.get("traces_scored") or 0)
    fully = (cf.get("traces_fully_correct") or 0) + (df.get("traces_fully_correct") or 0)

    # Step 3 — refutation
    s3_shown = of(S.counter_example, E.shown)
    s3_subs = of(S.counter_example, E.submitted)
    s3_payloads = [e.payload or {} for e in s3_subs]
    limit = task.step3_max_attempts
    success = bool(sess.counter_example_completed)
    closed = success or bool(limit and len(s3_subs) >= limit)

    # Code-mixed switching
    mixed = [v for v in views if v.version == "mixed"]
    switches = sum(1 for a, b in zip(views, views[1:]) if a.version != b.version and a.step == b.step)

    return {
        "session_id": sess.id,
        "participant_id": part.id,
        "student_identifier": part.student_identifier,
        "institute": part.institute,
        "native_language": part.native_language,
        "schooling_medium": part.schooling_medium,
        "english_proficiency": part.english_proficiency,
        "proficiency_band": _band(part.english_proficiency),
        "condition_row": part.condition_row,
        "position": sess.position,
        "variant": task.variant_key,
        "problem": task.problem_key,
        "form": task.form,
        "bug": task.bug_kind,
        # step 1
        "s1_attempts": len(s1_subs),
        "s1_first_correct": bool(s1_subs and s1_subs[0].is_correct),
        "s1_passed": bool(sess.io_pairs_completed),
        "s1_examples_requested": bool(sess.io_examples_shown),
        "s1_counterexample_in_pairs": any(p.get("is_counterexample") for p in pairs),
        "s1_seconds": _seconds(s1_shown[0].timestamp if s1_shown else None,
                               s1_first_ok.timestamp if s1_first_ok else None),
        # step 2
        "s2_done": s2_sub is not None,
        "s2_cell_accuracy": round(100 * cells_ok / cells_all, 1) if cells_all else None,
        "s2_fully_correct": bool(scored) and fully == scored,
        "s2_correct_at_buggy_line": cf.get("correct_at_buggy_line"),
        "s2_seconds": _seconds(s2_shown[0].timestamp if s2_shown else None,
                               s2_sub.timestamp if s2_sub else None),
        # step 3
        "s3_attempts": len(s3_subs),
        "s3_closed": closed,
        "s3_success": success,
        "s3_first_attempt_success": bool(s3_payloads and s3_payloads[0].get("fully_successful")),
        "s3_found_counterexample_input": any(p.get("is_counter_example") for p in s3_payloads),
        "s3_required_output_right_any": any(p.get("required_output_right") for p in s3_payloads),
        "s3_buggy_prediction_right_any": any(p.get("buggy_prediction_right") for p in s3_payloads),
        "s3_invalid_attempts": sum(1 for p in s3_payloads if p.get("invalid_reason")),
        "s3_seconds": _seconds(s3_shown[0].timestamp if s3_shown else None,
                               s3_subs[-1].timestamp if s3_subs else None),
        "s3_how_found": [p.get("how_found") for p in s3_payloads if p.get("how_found")],
        "s3_inputs": [p.get("call") for p in s3_payloads],
        # code-mixed
        "switched_to_mixed": bool(mixed),
        "spec_switches": switches,
        "seconds_to_first_switch": _seconds(sess.created_at, mixed[0].timestamp if mixed else None),
    }


# ---------------------------------------------------------------------------
# aggregate tables
# ---------------------------------------------------------------------------

def _cell(rows: List[dict]) -> dict:
    """The standard per-group block of Step 3 + timing measures."""
    closed = [r for r in rows if r["s3_closed"]]
    return {
        "sessions": len(rows),
        "finished": len(closed),
        "success": _rate(closed, lambda r: r["s3_success"]),
        "first_attempt_success": _rate(closed, lambda r: r["s3_first_attempt_success"]),
        "found_input_but_wrong_outputs": _rate(
            closed, lambda r: r["s3_found_counterexample_input"] and not r["s3_success"]),
        "median_s1_seconds": _median(r["s1_seconds"] for r in rows),
        "median_s3_seconds": _median(r["s3_seconds"] for r in closed),
    }


def analyse(db: Session, institute: Optional[str] = None) -> Dict:
    rows = session_rows(db, institute)
    by = lambda **kw: [r for r in rows if all(r[k] == v for k, v in kw.items())]  # noqa: E731

    participants = {r["participant_id"] for r in rows}
    by_participant = defaultdict(list)
    for r in rows:
        by_participant[r["participant_id"]].append(r)
    complete = {pid: rs for pid, rs in by_participant.items()
                if len(rs) == 2 and all(r["s3_closed"] for r in rs)}

    # --- RQ1 / RQ2: form x bug ------------------------------------------------
    form_bug = []
    for bug in BUGS:
        for form in FORMS:
            form_bug.append({"bug": bug, "bug_label": BUG_LABEL[bug], "form": form,
                             **_cell(by(form=form, bug=bug))})
    by_form = [{"form": f, **_cell(by(form=f))} for f in FORMS]

    def pct(form, bug):
        return next(c["success"]["pct"] for c in form_bug if c["form"] == form and c["bug"] == bug)

    effects = {}
    for bug in BUGS:
        d, c = pct("direct", bug), pct("contextualized", bug)
        effects[bug] = None if d is None or c is None else round(c - d, 1)
    benefit = (None if None in effects.values()
               else round(effects["buggy2"] - effects["buggy1"], 1))

    # --- within-participant: direct vs contextualized --------------------------
    def paired(rs_list):
        counts = {"both_correct": 0, "direct_only": 0, "contextualized_only": 0, "neither": 0}
        for rs in rs_list:
            d = next(r for r in rs if r["form"] == "direct")["s3_success"]
            c = next(r for r in rs if r["form"] == "contextualized")["s3_success"]
            key = ("both_correct" if d and c else "direct_only" if d
                   else "contextualized_only" if c else "neither")
            counts[key] += 1
        return {"participants": len(rs_list), **counts}

    ctx_bug = lambda rs: next(r for r in rs if r["form"] == "contextualized")["bug"]  # noqa: E731
    paired_table = [{"group": "All participants", **paired(list(complete.values()))}] + [
        {"group": f"Contextualized task had {BUG_LABEL[b]}",
         **paired([rs for rs in complete.values() if ctx_bug(rs) == b])}
        for b in BUGS
    ]

    # --- Step 1: task comprehension ---------------------------------------------
    step1 = []
    for form in FORMS:
        rs = by(form=form)
        step1.append({
            "form": form,
            "sessions": len(rs),
            "failed_first_attempt": _rate(rs, lambda r: r["s1_attempts"] and not r["s1_first_correct"]),
            "mean_attempts": _mean(r["s1_attempts"] for r in rs if r["s1_attempts"]),
            "requested_examples": _rate(rs, lambda r: r["s1_examples_requested"]),
            "never_passed": _rate(rs, lambda r: r["s1_attempts"] and not r["s1_passed"]),
            "median_seconds": _median(r["s1_seconds"] for r in rs),
        })
    step1_counterexamples = [
        {"form": f, "bug": b, "bug_label": BUG_LABEL[b],
         "already_had_counterexample": _rate(by(form=f, bug=b), lambda r: r["s1_counterexample_in_pairs"])}
        for b in BUGS for f in FORMS
    ]

    # --- Step 2: code tracing (should NOT differ by form) ------------------------
    step2 = []
    for form in FORMS:
        rs = [r for r in by(form=form) if r["s2_done"]]
        step2.append({
            "form": form,
            "sessions": len(rs),
            "mean_cell_accuracy_pct": _mean(r["s2_cell_accuracy"] for r in rs),
            "fully_correct": _rate(rs, lambda r: r["s2_fully_correct"]),
            "correct_at_buggy_line": _rate(
                [r for r in rs if r["s2_correct_at_buggy_line"] is not None],
                lambda r: r["s2_correct_at_buggy_line"]),
            "median_seconds": _median(r["s2_seconds"] for r in rs),
        })

    # --- Step 3 among students who understood the task and traced the code ----
    understood = [r for r in rows if r["s1_first_correct"] and r["s2_fully_correct"]]
    conditional = [
        {"form": f, "bug": b, "bug_label": BUG_LABEL[b],
         **_cell([r for r in understood if r["form"] == f and r["bug"] == b])}
        for b in BUGS for f in FORMS
    ]

    # --- source of failed refutations -------------------------------------------
    failures = []
    for form in FORMS:
        failed = [r for r in by(form=form) if r["s3_closed"] and not r["s3_success"]]
        failures.append({
            "form": form,
            "failed": len(failed),
            "task_misread": _rate(failed, lambda r: not r["s1_first_correct"]),
            "code_mistraced": _rate(failed, lambda r: r["s1_first_correct"] and not r["s2_fully_correct"]),
            "understood_both": _rate(failed, lambda r: r["s1_first_correct"] and r["s2_fully_correct"]),
            "found_input_wrong_outputs": _rate(failed, lambda r: r["s3_found_counterexample_input"]),
            "invalid_or_implausible_attempts": sum(r["s3_invalid_attempts"] for r in failed),
        })

    # --- RQ3: code-mixed use -----------------------------------------------------
    switching = [
        {"form": f, "sessions": len(by(form=f)),
         "switched": _rate(by(form=f), lambda r: r["switched_to_mixed"]),
         "mean_switches": _mean(r["spec_switches"] for r in by(form=f)),
         "median_seconds_to_first_switch": _median(r["seconds_to_first_switch"] for r in by(form=f))}
        for f in FORMS
    ]
    switching_by_language = []
    for lang in sorted({r["native_language"] for r in rows if r["native_language"]}):
        rs = [r for r in rows if r["native_language"] == lang]
        switching_by_language.append({"native_language": lang, "sessions": len(rs),
                                      "switched": _rate(rs, lambda r: r["switched_to_mixed"])})

    # --- by English reading proficiency -----------------------------------------
    proficiency = []
    for band, _ in PROFICIENCY_BANDS:
        for form in FORMS:
            rs = [r for r in rows if r["proficiency_band"] == band and r["form"] == form]
            closed = [r for r in rs if r["s3_closed"]]
            proficiency.append({
                "band": band, "form": form, "sessions": len(rs),
                "step1_first_attempt_correct": _rate(rs, lambda r: r["s1_first_correct"]),
                "switched": _rate(rs, lambda r: r["switched_to_mixed"]),
                "success": _rate(closed, lambda r: r["s3_success"]),
                "median_s1_seconds": _median(r["s1_seconds"] for r in rs),
            })

    # --- per variant and assignment balance --------------------------------------
    variants = [{"variant": v, **_cell(by(variant=v))}
                for v in sorted({r["variant"] for r in rows})]
    by_institute = defaultdict(set)
    for r in rows:
        by_institute[r["institute"]].add(r["participant_id"])

    return {
        "filter": {"institute": institute},
        "overview": {
            "participants": len(participants),
            "participants_complete": len(complete),
            "sessions": len(rows),
            "sessions_finished": sum(1 for r in rows if r["s3_closed"]),
            "by_institute": {k: len(v) for k, v in sorted(by_institute.items())},
        },
        "by_form": by_form,
        "form_bug": form_bug,
        "context_effect_pp": effects,
        "context_benefit_pp": benefit,
        "paired": paired_table,
        "step1": step1,
        "step1_counterexamples": step1_counterexamples,
        "step2": step2,
        "conditional": conditional,
        "failures": failures,
        "switching": switching,
        "switching_by_language": switching_by_language,
        "proficiency": proficiency,
        "variants": variants,
    }
