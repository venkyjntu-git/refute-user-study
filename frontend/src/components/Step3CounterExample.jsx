import React, { useEffect, useState } from "react";
import { api } from "../api";
import { extractFunctionName } from "../utils";
import SpecPanel from "./SpecPanel";

export default function Step3CounterExample({ session, buggyCode, onNext, nextError, hasNextTask }) {
  const [args, setArgs] = useState("");
  const [predictedCorrect, setPredictedCorrect] = useState("");
  const [predictedBuggy, setPredictedBuggy] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [myWork, setMyWork] = useState(null);

  const funcName = extractFunctionName(session.function_signature);

  useEffect(() => {
    api.markShown(session.session_id, "counter_example").catch(() => {});
    // Recap of the student's own Step 1 + Step 2 answers, fetched fresh
    // from the server rather than kept in lifted component state — robust
    // to a page refresh between steps, and guaranteed to contain nothing
    // beyond what the student themselves submitted (see get_my_work's
    // allowlisting in main.py).
    api.getMyWork(session.session_id).then(setMyWork).catch(() => {});
  }, [session.session_id]);

  const handleSubmit = async () => {
    if (!args.trim()) {
      setError("Please enter the arguments for your counter-example call.");
      return;
    }
    if (!predictedCorrect.trim() || !predictedBuggy.trim()) {
      setError("Please predict both outputs before submitting — that's the point of this step.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const call = `${funcName}(${args.trim()})`;
      const res = await api.submitCounterExample(
        session.session_id, call, predictedCorrect.trim(), predictedBuggy.trim()
      );
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Step 3: Find a counter-example</h2>

      <h3>Task Description</h3>
      <SpecPanel session={session} step="counter_example" />

      <h3>Buggy code</h3>
      <pre className="code-block">{buggyCode}</pre>

      {myWork && (
        <>
          <h3 className="section-divider">Your Step 1 answers</h3>
          {myWork.io_pairs.map((p, idx) => (
            <div className="result-item" key={idx}>{p.call} → {p.expected}</div>
          ))}

          <h3 className="section-divider">Your Step 2 answers</h3>
          {myWork.control_flow.map((t) => (
            <div className="trace-block" key={t.call}>
              <h4>Control flow: <code>{t.call}</code></h4>
              <div className="table-scroll">
                <table className="trace-table">
                  <thead>
                    <tr><th>Line</th><th>Your count</th></tr>
                  </thead>
                  <tbody>
                    {t.rows.map((r) => (
                      <tr key={r.lineno}>
                        <td><code>{r.lineno}: {r.line_text}</code></td>
                        <td>{r.student_count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p>Your answer for the return value: <code>{t.student_final_output}</code></p>
            </div>
          ))}
          {myWork.data_flow.map((t) => (
            <div className="trace-block" key={t.call}>
              <h4>Data flow: <code>{t.call}</code></h4>
              <div className="table-scroll">
                <table className="trace-table">
                  <thead>
                    <tr>
                      <th>Step</th>
                      <th>Line</th>
                      {t.rows[0] && Object.keys(t.rows[0].vars).map((n) => (
                        <th key={n}><code>{n}</code></th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {t.rows.map((r) => (
                      <tr key={r.step}>
                        <td>{r.step}</td>
                        <td><code>{r.lineno}: {r.line_text}</code></td>
                        {Object.entries(r.vars).map(([n, v]) => <td key={n}>{v}</td>)}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p>Your answer for the return value: <code>{t.student_final_output}</code></p>
            </div>
          ))}
          {myWork.mutation_prompt && (
            <div className="trace-block">
              <h4>Your reflection question response</h4>
              {myWork.mutation_new_line_text && (
                <p>Line {myWork.mutation_line_number} changed to: <code>{myWork.mutation_new_line_text}</code></p>
              )}
              <p>{myWork.mutation_prompt}</p>
              <p className="result-item">{myWork.mutation_response}</p>
            </div>
          )}
        </>
      )}

      {session.step3_max_attempts ? (
        <StudyRefutation
          session={session}
          funcName={funcName}
          onNext={onNext}
          nextError={nextError}
          hasNextTask={hasNextTask}
        />
      ) : (
      <>
      <p>
        Give one input for which the buggy code produces a <em>different</em>{" "}
        result than the correct code — that's your refutation. Before you find
        out either real output, predict both: what you think the{" "}
        <strong>correct</strong> code returns, and what you think the{" "}
        <strong>buggy</strong> code above returns, for the same input.
      </p>

      <label>Counter-example call</label>
      <div className="call-input">
        <code className="call-fixed">{funcName}(</code>
        <input
          type="text"
          placeholder="e.g. 1, 3, 5"
          aria-label="Counter-example arguments"
          value={args}
          onChange={(e) => setArgs(e.target.value)}
        />
        <code className="call-fixed">)</code>
      </div>

      <label>What do you think the correct code returns?</label>
      <input
        type="text"
        placeholder="e.g. 5"
        value={predictedCorrect}
        onChange={(e) => setPredictedCorrect(e.target.value)}
      />

      <label>What do you think the buggy code above returns?</label>
      <input
        type="text"
        placeholder="e.g. 3"
        value={predictedBuggy}
        onChange={(e) => setPredictedBuggy(e.target.value)}
      />

      {error && <div className="error-banner">{error}</div>}

      {result && (
        <div style={{ marginTop: 16 }}>
          <div className="result-item">
            {result.call}
            {result.error ? (
              <span className="result-badge incorrect">ERROR: {result.error}</span>
            ) : (
              <>
                <br />
                Your prediction — correct code: {result.predicted_correct_output}{" "}
                <span className={`result-badge ${result.correct_prediction_right ? "correct" : "incorrect"}`}>
                  {result.correct_prediction_right ? "RIGHT" : "WRONG"}
                </span>
                <br />
                Your prediction — buggy code: {result.predicted_buggy_output}{" "}
                <span className={`result-badge ${result.buggy_prediction_right ? "correct" : "incorrect"}`}>
                  {result.buggy_prediction_right ? "RIGHT" : "WRONG"}
                </span>
              </>
            )}
          </div>
          {result.fully_successful ? (
            <div className="success-banner">
              Confirmed — this is a valid counter-example, and both of your
              predictions were right.{" "}
              {hasNextTask
                ? "This problem is complete."
                : "You've completed all problems in this study. Thank you!"}
            </div>
          ) : result.is_counter_example ? (
            <div className="notice">
              This input is a valid counter-example, but at least one of your
              predictions was wrong — think through why, then try again (a
              new input, or the same one with revised predictions).
            </div>
          ) : (
            <div className="error-banner">
              Not a counter-example — both outputs match. Try a different input.
            </div>
          )}
        </div>
      )}

      {!(result && result.fully_successful) && (
        <button onClick={handleSubmit} disabled={loading}>
          {loading ? "Checking..." : "Submit counter-example"}
        </button>
      )}

      {result && result.fully_successful && (
        <>
          {nextError && <div className="error-banner">{nextError}</div>}
          <button onClick={onNext}>
            {hasNextTask ? "Next problem" : "Finish study"}
          </button>
        </>
      )}
      </>
      )}
    </div>
  );
}

// Study-mode Step 3 (the WG design): an input on which the program fails,
// plus the output the TASK requires for it — no prediction of what the
// program returns — with a limited number of attempts. Feedback is one bit
// (refuted or not); only an input that breaks the task's rules says why.
function StudyRefutation({ session, funcName, onNext, nextError, hasNextTask }) {
  const [args, setArgs] = useState("");
  const [requiredOutput, setRequiredOutput] = useState("");
  const [buggyOutput, setBuggyOutput] = useState("");
  const [howFound, setHowFound] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const maxAttempts = session.step3_max_attempts;
  const attemptsRemaining = result
    ? result.attempts_remaining
    : maxAttempts - (session.step3_attempts_used || 0);
  const closed = result && result.closed;

  const handleSubmit = async () => {
    if (!args.trim()) {
      setError("Please enter the arguments for your input.");
      return;
    }
    if (!requiredOutput.trim() || !buggyOutput.trim()) {
      setError("Please give both outputs: the one the task requires, and the one the code above returns.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.submitRefutation(
        session.session_id, `${funcName}(${args.trim()})`, requiredOutput.trim(),
        buggyOutput.trim(), howFound.trim() || null,
      );
      setResult(res);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <p>
        Give one input on which the code above does <em>not</em> do what the
        task requires. For that input, give both the output that the{" "}
        <strong>task</strong> requires and the output that the{" "}
        <strong>code above</strong> returns.
      </p>
      {session.form === "contextualized" && (
        <div className="notice">
          Your input must be realistic for the situation described in the
          task — the kind of data that could really occur there.
        </div>
      )}
      <p className="result-hint">
        You have {attemptsRemaining} of {maxAttempts} attempt{maxAttempts === 1 ? "" : "s"} left.
      </p>

      <label>Your input</label>
      <div className="call-input">
        <code className="call-fixed">{funcName}(</code>
        <input
          type="text"
          placeholder="arguments"
          aria-label="Input arguments"
          value={args}
          disabled={closed}
          onChange={(e) => setArgs(e.target.value)}
        />
        <code className="call-fixed">)</code>
      </div>

      <label>Output the task requires for this input</label>
      <input
        type="text"
        value={requiredOutput}
        disabled={closed}
        onChange={(e) => setRequiredOutput(e.target.value)}
      />

      <label>Output the code above returns for this input</label>
      <input
        type="text"
        value={buggyOutput}
        disabled={closed}
        onChange={(e) => setBuggyOutput(e.target.value)}
      />

      <label>How did you find this input? (optional)</label>
      <textarea
        value={howFound}
        disabled={closed}
        onChange={(e) => setHowFound(e.target.value)}
      />

      {error && <div className="error-banner">{error}</div>}

      {result && (
        result.fully_successful ? (
          <div className="success-banner">
            Correct — this input shows that the code is wrong.
          </div>
        ) : result.invalid_reason ? (
          <div className="error-banner">{result.invalid_reason}</div>
        ) : (
          <div className="error-banner">
            Not correct: either the code does what the task requires on this
            input, or at least one of the two outputs you gave is wrong.
          </div>
        )
      )}
      {closed && !result.fully_successful && (
        <div className="notice">You have used all your attempts for this problem.</div>
      )}

      {!closed && (
        <button onClick={handleSubmit} disabled={loading}>
          {loading ? "Checking..." : "Submit"}
        </button>
      )}
      {closed && (
        <>
          {nextError && <div className="error-banner">{nextError}</div>}
          <button onClick={onNext}>
            {hasNextTask ? "Next problem" : "Finish study"}
          </button>
        </>
      )}
    </>
  );
}
