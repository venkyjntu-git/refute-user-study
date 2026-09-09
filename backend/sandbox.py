"""
Sandboxed-ish execution of a single-function code string against a call
expression, in an isolated subprocess.

IMPORTANT CAVEAT (read before deploying beyond a supervised user study):
This uses a separate OS process with `python -I` (isolated mode, ignores
PYTHONPATH/site dirs), a short wall-clock timeout, and (on POSIX) CPU/memory
rlimits. It is NOT a hardened multi-tenant sandbox — there is no seccomp,
no container/VM boundary, and no filesystem/network jail. It is adequate for
a supervised study where the "attacker" is a CS1 student typing normal
Python expressions, not for an adversarial/public deployment. For that,
run this in a locked-down container (e.g. gVisor/firecracker) or use a
service like Judge0/Piston.
"""
import ast
import json
import subprocess
import sys
#import resource
import tempfile
import os
import textwrap
from dataclasses import dataclass
from typing import Optional, Any


if os.name == "posix":
    import resource
else:
    resource = None

TIMEOUT_SECONDS = 5
MAX_MEMORY_BYTES = 256 * 1024 * 1024  # 256MB
MAX_CPU_SECONDS = 5
# Hard cap on rows in a captured trace. Tracing is slow, and a loop-heavy task
# must not produce a 300-row table for a student to fill in by hand.
MAX_TRACE_STEPS = 40

# Dropdown sentinel for "execution left the function" on the last trace row.
NEXT_LINE_END = "return / end"


@dataclass
class ExecResult:
    ok: bool
    value_repr: Optional[str] = None  # repr() of the returned value, JSON-safe string
    error: Optional[str] = None


@dataclass
class TraceStep:
    """One executed line of the function, with the state it produced."""
    step: int             # 1-based position in execution order
    lineno: int           # line number within the function source (1-based)
    line_text: str        # the source text of that line, dedented
    depth: int            # call depth, 0 for the outermost frame (recursion > 0)
    # variable name -> repr() of its value AFTER this line finished executing.
    # Names not yet bound at this point are absent from the dict.
    vars_after: dict
    # line number executed next within this function, or NEXT_LINE_END when the
    # function returned / execution left it.
    next_line: str


@dataclass
class TraceCapture:
    ok: bool
    steps: Optional[list] = None        # list[TraceStep]
    var_names: Optional[list] = None    # union of local names, first-appearance order
    return_repr: Optional[str] = None   # repr() of the function's return value
    code_lines: Optional[list] = None   # [(lineno, text)] for every line of the source
    truncated: bool = False
    error: Optional[str] = None


def _limit_resources():
    if resource is None:
        return
    # POSIX only; no-op / best-effort on other platforms.
    try:
        resource.setrlimit(resource.RLIMIT_CPU, (MAX_CPU_SECONDS, MAX_CPU_SECONDS))
        resource.setrlimit(resource.RLIMIT_AS, (MAX_MEMORY_BYTES, MAX_MEMORY_BYTES))
    except Exception:
        pass


_RUNNER_TEMPLATE = """
import sys, json, ast

CODE = {code!r}
CALL = {call!r}

def main():
    namespace = {{"__name__": "__student_code__"}}
    try:
        exec(compile(CODE, "<student_code>", "exec"), namespace)
    except Exception as e:
        print(json.dumps({{"ok": False, "error": f"Error defining function: {{e!r}}"}}))
        return
    try:
        result = eval(compile(CALL, "<call>", "eval"), namespace)
    except Exception as e:
        print(json.dumps({{"ok": False, "error": f"Error calling function: {{e!r}}"}}))
        return
    try:
        # Use repr so ints/floats/strings/lists/tuples round-trip unambiguously.
        value_repr = repr(result)
    except Exception as e:
        print(json.dumps({{"ok": False, "error": f"Could not represent result: {{e!r}}"}}))
        return
    print(json.dumps({{"ok": True, "value_repr": value_repr}}))

main()
"""


def run_call(code: str, call: str) -> ExecResult:
    """
    Execute `code` (defines exactly one function) in a fresh subprocess, then
    evaluate `call` (e.g. "max_of_three(1, 2, 3)") against the resulting
    namespace, returning the repr() of the result.
    """
    # Basic sanity-check the call is a syntactically valid single call
    # expression before we even spawn a process.
    syntax_error = _check_call_syntax(call)
    if syntax_error:
        return ExecResult(ok=False, error=syntax_error)

    script = _RUNNER_TEMPLATE.format(code=code, call=call)
    payload, error = _exec_script(script)
    if error is not None:
        return ExecResult(ok=False, error=error)
    if not payload.get("ok"):
        return ExecResult(ok=False, error=payload.get("error", "Unknown execution error."))

    return ExecResult(ok=True, value_repr=payload["value_repr"])


def _check_call_syntax(call: str) -> Optional[str]:
    """Return an error message if `call` is not a single function call expression."""
    try:
        parsed = ast.parse(call, mode="eval")
        if not isinstance(parsed.body, ast.Call):
            return "Input must be a single function call, e.g. func(1, 2)."
    except SyntaxError as e:
        return f"Invalid call syntax: {e}"
    return None


def _exec_script(script: str):
    """
    Run `script` in an isolated subprocess and parse its final line of stdout as
    JSON. Returns (payload, None) on success or (None, error_message) on failure.
    Shared by run_call and capture_trace so both get the same timeout/rlimits.
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script)
        script_path = f.name

    try:
        preexec = _limit_resources if os.name == "posix" else None
        proc = subprocess.run(
            [sys.executable, "-I", script_path],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            preexec_fn=preexec,
        )
    except subprocess.TimeoutExpired:
        return None, "Execution timed out (possible infinite loop)."
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass

    if proc.returncode != 0 and not proc.stdout.strip():
        stderr = proc.stderr.strip()
        if not stderr:
            # Killed with nothing on stderr — almost always RLIMIT_CPU firing
            # before the wall-clock timeout (an infinite loop), or RLIMIT_AS.
            return None, ("Execution was killed before it finished — most likely "
                          "an infinite loop or a resource limit.")
        return None, f"Process error: {stderr[-500:]}"

    try:
        return json.loads(proc.stdout.strip().splitlines()[-1]), None
    except Exception:
        return None, f"Could not parse execution output: {proc.stdout!r} {proc.stderr!r}"


def values_equal(value_repr: str, expected_str: str) -> bool:
    """
    Compare an actual result's repr() against a student/task-provided
    expected string. Try literal-eval on both sides first (so "3" == 3,
    "[1, 2]" == [1,2]); fall back to stripped string equality.
    """
    def _try_literal(s: str) -> Any:
        try:
            return ast.literal_eval(s)
        except Exception:
            return None

    actual_val = _try_literal(value_repr)
    expected_val = _try_literal(expected_str)

    if actual_val is not None or value_repr.strip() in ("None",):
        if expected_val is not None or expected_str.strip() in ("None",):
            try:
                return actual_val == expected_val
            except Exception:
                pass

    return value_repr.strip() == expected_str.strip()


# ---------------------------------------------------------------------------
# execution trace capture (Step 2 of the study)
# ---------------------------------------------------------------------------
#
# The trace table shown to students, and the answer key it is graded against,
# are both derived from this capture — task authors only supply the sample
# input calls. This mirrors Russell's two-phase generation (execute -> JSON
# trace -> questions) rather than requiring hand-authored expected states.
#
# The body below is injected verbatim (no str.format) so it can use braces
# freely; the three constants are prepended as a literal header instead.

_TRACER_BODY = r'''
STUDENT_FILE = "<student_code>"

events = []
truncated = [False]
uid_by_id = {}
next_uid = [0]


def safe_repr(value):
    try:
        return repr(value)
    except Exception:
        return "<unrepresentable>"


def snapshot(frame):
    out = {}
    for name, value in frame.f_locals.items():
        out[name] = safe_repr(value)
    return out


def is_student_frame(frame):
    code = frame.f_code
    return code.co_filename == STUDENT_FILE and code.co_name != "<module>"


def depth_of(frame):
    """Nesting depth within the student's own code (0 = outermost call)."""
    depth = 0
    parent = frame.f_back
    while parent is not None:
        if is_student_frame(parent):
            depth += 1
        parent = parent.f_back
    return depth


def uid_for(frame):
    """
    Stable per-frame id. Keyed on id(frame), but popped when the frame returns
    so that a later frame reusing the same address gets a fresh uid.
    """
    key = id(frame)
    if key not in uid_by_id:
        uid_by_id[key] = next_uid[0]
        next_uid[0] += 1
    return uid_by_id[key]


def local_tracer(frame, event, arg):
    if event not in ("line", "return"):
        return local_tracer
    if len(events) >= MAX_STEPS:
        truncated[0] = True
        sys.settrace(None)
        return None

    record = {
        "kind": event,
        "uid": uid_for(frame),
        "lineno": frame.f_lineno,
        "depth": depth_of(frame),
        "vars": snapshot(frame),
    }
    if event == "return":
        record["ret"] = safe_repr(arg)
        uid_by_id.pop(id(frame), None)
    events.append(record)
    return local_tracer


def global_tracer(frame, event, arg):
    if not is_student_frame(frame):
        return None
    return local_tracer


def build_rows(source_lines):
    """
    Turn the flat event list into one row per executed line.

    A 'line' event fires BEFORE its line runs, so the state produced by the
    line at event i is the state recorded at the next event in the SAME frame.
    That next event's lineno is also what executes next; if it is the frame's
    'return' event, execution left the function instead.
    """
    next_in_frame = {}
    for idx in range(len(events) - 1, -1, -1):
        uid = events[idx]["uid"]
        if uid in next_in_frame:
            events[idx]["next_idx"] = next_in_frame[uid]
        next_in_frame[uid] = idx

    rows = []
    for idx, ev in enumerate(events):
        if ev["kind"] != "line":
            continue
        nxt_idx = ev.get("next_idx")
        if nxt_idx is None:
            # No follow-up event for this frame: the trace was cut short by
            # MAX_STEPS (or an exception). We cannot say what this line did.
            truncated[0] = True
            continue
        nxt = events[nxt_idx]
        lineno = ev["lineno"]
        rows.append({
            "step": len(rows) + 1,
            "lineno": lineno,
            "line_text": source_lines[lineno - 1] if 0 < lineno <= len(source_lines) else "",
            "depth": ev["depth"],
            "vars_after": nxt["vars"],
            "next_line": NEXT_LINE_END if nxt["kind"] == "return" else str(nxt["lineno"]),
        })
    return rows


def main():
    namespace = {"__name__": "__student_code__"}
    try:
        exec(compile(CODE, STUDENT_FILE, "exec"), namespace)
    except Exception as e:
        print(json.dumps({"ok": False, "error": "Error defining function: %r" % (e,)}))
        return

    call_code = compile(CALL, "<call>", "eval")
    sys.settrace(global_tracer)
    try:
        result = eval(call_code, namespace)
    except Exception as e:
        sys.settrace(None)
        print(json.dumps({"ok": False, "error": "Error calling function: %r" % (e,)}))
        return
    finally:
        sys.settrace(None)

    source_lines = [line.rstrip() for line in CODE.splitlines()]
    rows = build_rows(source_lines)

    var_names = []
    for row in rows:
        for name in row["vars_after"]:
            if name not in var_names:
                var_names.append(name)

    print(json.dumps({
        "ok": True,
        "rows": rows,
        "var_names": var_names,
        "return_repr": safe_repr(result),
        "code_lines": [[i + 1, text] for i, text in enumerate(source_lines)],
        "truncated": truncated[0],
    }))


main()
'''


def capture_trace(code: str, call: str, max_steps: int = MAX_TRACE_STEPS) -> TraceCapture:
    """
    Execute `call` against `code` under sys.settrace in an isolated subprocess
    and return one TraceStep per executed line, in execution order.

    This is the ground truth for the Step 2 trace table: the skeleton sent to
    the browser is derived from it with the answers stripped out, and the
    student's submission is graded against a fresh capture on the server.

    Two limitations worth knowing when authoring tasks:

    * Loops produce a row per iteration, so a task with a big loop hits
      `max_steps` and comes back truncated. Pick small sample inputs — a
      39-row table is a safety cap, not something a student should fill in.
    * Recursion is recorded (each row carries `depth`), but rows are laid out
      in one linear sequence, and a row whose frame recurses reports
      `NEXT_LINE_END` when that frame eventually returns rather than showing
      the jump into the nested call. Non-recursive tasks are unaffected.
    """
    syntax_error = _check_call_syntax(call)
    if syntax_error:
        return TraceCapture(ok=False, error=syntax_error)

    header = "import sys, json\nCODE = %r\nCALL = %r\nMAX_STEPS = %r\nNEXT_LINE_END = %r\n" % (
        code, call, max_steps, NEXT_LINE_END,
    )
    payload, error = _exec_script(header + _TRACER_BODY)
    if error is not None:
        return TraceCapture(ok=False, error=error)
    if not payload.get("ok"):
        return TraceCapture(ok=False, error=payload.get("error", "Unknown execution error."))

    steps = [
        TraceStep(
            step=row["step"],
            lineno=row["lineno"],
            line_text=row["line_text"],
            depth=row["depth"],
            vars_after=row["vars_after"],
            next_line=row["next_line"],
        )
        for row in payload["rows"]
    ]
    return TraceCapture(
        ok=True,
        steps=steps,
        var_names=payload["var_names"],
        return_repr=payload["return_repr"],
        code_lines=[tuple(pair) for pair in payload["code_lines"]],
        truncated=payload["truncated"],
    )
