import React, { useEffect, useState } from "react";
import { api } from "../api";
import { extractFunctionName } from "../utils";

const emptyPair = () => ({ args: "", expected: "" });

export default function Step1IOPairs({ session, onCompleted }) {
  const [pairs, setPairs] = useState([emptyPair(), emptyPair(), emptyPair()]);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const funcName = extractFunctionName(session.function_signature);

  useEffect(() => {
    // task_description + io_pairs 'shown' events are logged server-side
    // when the session starts, so nothing to do here — but if a student
    // re-enters this step after a retry we don't want to double count,
    // so we only mark-shown once via the session start. Left here as a
    // hook point if you want per-render granularity instead.
  }, []);

  const updatePair = (idx, field, value) => {
    const next = [...pairs];
    next[idx] = { ...next[idx], [field]: value };
    setPairs(next);
  };

  const handleSubmit = async () => {
    if (pairs.some((p) => !p.args.trim() || !p.expected.trim())) {
      setError("Please fill in all three argument/expected-output fields.");
      return;
    }
    const submissions = pairs.map((p) => ({
      call: `${funcName}(${p.args.trim()})`,
      expected: p.expected,
    }));
    // Quick client-side check on the raw string; the server does the
    // authoritative check (it compares parsed calls, so "f(1,2)" and
    // "f(1, 2)" are also caught as duplicates there).
    const calls = submissions.map((p) => p.call);
    if (new Set(calls).size < calls.length) {
      setError("Please use three different arguments — at least two of your pairs are identical.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.submitIOPairs(session.session_id, submissions);
      setResults(res);
      if (res.all_correct) {
        onCompleted(res.buggy_code, res.trace_tables, res.data_flow_tables);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Task Description</h2>
      <p>{session.description}</p>
      <pre className="code-block">{session.function_signature}
    ...</pre>

      <h3 style={{ marginTop: 28 }}>Step 1: Give three input/output pairs</h3>
      <p style={{ color: "#555", fontSize: 14 }}>
        Give the arguments for each call (comma-separated, in order) and the
        output you expect it to produce.
      </p>

      {pairs.map((pair, idx) => (
        <div className="pair-row" key={idx}>
          <div>
            <label>Call #{idx + 1}</label>
            <div className="call-input">
              <code className="call-fixed">{funcName}(</code>
              <input
                type="text"
                placeholder="e.g. 1, 2, 3"
                aria-label={`Call #${idx + 1} arguments`}
                value={pair.args}
                onChange={(e) => updatePair(idx, "args", e.target.value)}
              />
              <code className="call-fixed">)</code>
            </div>
          </div>
          <div>
            <label>Expected output</label>
            <input
              type="text"
              placeholder="e.g. 3"
              value={pair.expected}
              onChange={(e) => updatePair(idx, "expected", e.target.value)}
            />
          </div>
        </div>
      ))}

      {error && <div className="error-banner">{error}</div>}

      {results && (
        <div style={{ marginTop: 16 }}>
          {/* Which pairs were wrong, but never what the right output was —
              otherwise the student can copy the answers back on the next
              attempt and the step stops measuring spec comprehension. */}
          {results.results.map((r, idx) => (
            <div className="result-item" key={idx}>
              {r.call} — you said {r.expected}
              {r.could_not_run ? (
                <>
                  <span className="result-badge incorrect">COULDN'T RUN</span>
                  <div className="result-hint">
                    Check the number and format of your arguments.
                  </div>
                </>
              ) : (
                <span className={`result-badge ${r.correct ? "correct" : "incorrect"}`}>
                  {r.correct ? "CORRECT" : "INCORRECT"}
                </span>
              )}
            </div>
          ))}
          {results.all_correct ? (
            <div className="success-banner">
              All three pairs correct! Moving to the next step...
            </div>
          ) : (
            <div className="error-banner">
              At least one pair is incorrect. Please revise and resubmit.
            </div>
          )}
        </div>
      )}

      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Checking..." : "Submit pairs"}
      </button>
    </div>
  );
}
