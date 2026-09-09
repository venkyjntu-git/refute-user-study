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


@dataclass
class ExecResult:
    ok: bool
    value_repr: Optional[str] = None  # repr() of the returned value, JSON-safe string
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
    try:
        parsed = ast.parse(call, mode="eval")
        if not isinstance(parsed.body, ast.Call):
            return ExecResult(ok=False, error="Input must be a single function call, e.g. func(1, 2).")
    except SyntaxError as e:
        return ExecResult(ok=False, error=f"Invalid call syntax: {e}")

    script = _RUNNER_TEMPLATE.format(code=code, call=call)

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
        return ExecResult(ok=False, error="Execution timed out (possible infinite loop).")
    finally:
        try:
            os.unlink(script_path)
        except OSError:
            pass

    if proc.returncode != 0 and not proc.stdout.strip():
        return ExecResult(ok=False, error=f"Process error: {proc.stderr.strip()[-500:]}")

    try:
        payload = json.loads(proc.stdout.strip().splitlines()[-1])
    except Exception:
        return ExecResult(ok=False, error=f"Could not parse execution output: {proc.stdout!r} {proc.stderr!r}")

    if not payload.get("ok"):
        return ExecResult(ok=False, error=payload.get("error", "Unknown execution error."))

    return ExecResult(ok=True, value_repr=payload["value_repr"])


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
