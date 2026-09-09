# Refute-Problem Difficulty Study — Web App

FastAPI backend + React frontend implementing the 4-step study flow:

1. **Task description + 3 I/O pairs** — student writes `funcname(args)` /
   expected-output pairs; checked live against the correct code.
2. **Trace buggy code** — shown once all 3 pairs are correct, with two fixed
   sample inputs to hand-trace.
3. **Counter-example** — student submits one input; backend runs it against
   both correct and buggy code and reports match/mismatch.
4. **Timing** — every step logs a `shown` and `submitted` server timestamp
   per attempt, so per-step and per-attempt durations are computed from the
   data, not guessed client-side.

## Quick start

### Backend
```bash
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python seed_data.py          # inserts the sample max_of_three task (id=1)
uvicorn main:app --reload --port 8000
```
API docs: http://localhost:8000/docs

### Frontend
```bash
cd frontend
npm install
npm start
```
Runs on http://localhost:3000 and proxies `/api/*` to `localhost:8000`
(see `"proxy"` in `package.json`; set `REACT_APP_API_BASE` instead if you
deploy them separately).

## Data model / timing

`StepEvent` rows (`backend/models.py`) are the whole timing story:

| step             | event_type | when it's written                                   |
|------------------|-----------|-------------------------------------------------------|
| task_description | shown     | session start                                          |
| io_pairs         | shown     | session start (shown alongside the description)        |
| io_pairs         | submitted | every Step-1 submission (`attempt_number` increments)  |
| buggy_trace      | shown     | first time Step 1 is fully correct                      |
| buggy_trace      | submitted | every Step-2 submission                                 |
| counter_example  | shown     | first time Step 2 is submitted                           |
| counter_example  | submitted | every Step-3 submission                                  |

Time-on-step = `submitted.timestamp - most_recent_shown.timestamp` for that
`(session_id, step)` pair — compute this in your analysis script rather than
storing a duplicate duration column, so re-shows (e.g. a page refresh) don't
corrupt the record.

Export everything as CSV for stats:
```
GET /api/admin/export.csv
```
or pull one session's full event log as JSON:
```
GET /api/admin/sessions/{session_id}/events
```

## Adding tasks for the study

Add rows to the `tasks` table (or extend `seed_data.py`) with:
- `description` — shown verbatim in Step 1
- `function_signature` — display-only header shown above the I/O pair form
- `correct_code` / `buggy_code` — full single-function Python source
- `trace_sample_inputs` — JSON list of exactly the calls you want traced in
  Step 2 (design these to be genuinely informative — e.g. one input that
  happens to still produce the right answer under the bug, and one that
  doesn't, mirrors how instructors usually pick trace inputs)

## Execution sandboxing — read before running this on students' machines/servers

`backend/sandbox.py` runs each function call in a **separate Python
subprocess** (`python -I`, isolated mode) with a wall-clock timeout and
best-effort CPU/memory `rlimit`s on POSIX. This stops accidental infinite
loops or runaway memory use and prevents student input from touching the
FastAPI process's own namespace. It is **not** a hardened multi-tenant
sandbox: there's no container/VM boundary, no seccomp filter, and no
network/filesystem jail, so a student who deliberately wrote malicious code
(rather than a CS1 bug) could still do things a subprocess can do (e.g. read
files the server process can read).

For a supervised, IRB-style user study where the "attacker" is a CS1 student
typing ordinary buggy expressions, this is a reasonable trade-off. If you're
deploying this as an open, unsupervised, public-facing tool, swap
`sandbox.run_call` for a real isolated execution service (Docker container
with `--network none` + strict cgroup limits, gVisor/Firecracker, or a
hosted code-execution API like Judge0/Piston) — the function signature
(`run_call(code, call) -> ExecResult`) is designed so that's a drop-in swap.

## Extending for other languages (e.g. C for CS1)

The pipeline (I/O pairs → buggy trace → counter-example, each timestamped)
is language-agnostic. To support C:
- Replace `sandbox.run_call` with a compile-then-run step (`gcc`, temp
  binary, subprocess with the same rlimits/timeout).
- `values_equal` will need a C-output-aware comparison (stdout string
  compare is simplest if the student's function prints instead of returns).

## Known simplifications worth deciding on before running the real study

- **Retries**: Step 1 allows unlimited resubmission attempts (all logged via
  `attempt_number`) until all 3 pairs are correct. If you want to cap
  attempts or study give-up behavior, gate `/api/step1/submit` on attempt
  count and add a "skip" event type.
- **Float outputs**: `values_equal`/counter-example comparison uses exact
  `repr()` equality. If any task involves floats, add a tolerance-based
  comparison instead of strict inequality/equality.
- **Auth**: `student_identifier` is a free-text field, not authenticated.
  Fine for a lab study with an issued ID; add real auth if deploying broadly.
