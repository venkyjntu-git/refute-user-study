import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function Step2Trace({ session, buggyCode, sampleInputs, onCompleted }) {
  const [outputs, setOutputs] = useState(sampleInputs.map(() => ""));
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.markShown(session.session_id, "buggy_trace").catch(() => {});
  }, [session.session_id]);

  const handleSubmit = async () => {
    if (outputs.some((o) => !o.trim())) {
      setError("Please fill in the traced output for every sample input.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const traces = sampleInputs.map((call, idx) => ({
        call,
        student_output: outputs[idx],
      }));
      const res = await api.submitTraces(session.session_id, traces);
      setResults(res);
      onCompleted();
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Step 2: Trace the buggy code</h2>
      <p>
        Here is the buggy implementation of the function. For each sample
        input below, trace through the code by hand and write down what it
        actually outputs.
      </p>
      <pre className="code-block">{buggyCode}</pre>

      {sampleInputs.map((call, idx) => (
        <div className="pair-row" key={idx} style={{ gridTemplateColumns: "1fr 1fr" }}>
          <div>
            <label>Sample input</label>
            <input type="text" value={call} readOnly />
          </div>
          <div>
            <label>Your traced output</label>
            <input
              type="text"
              placeholder="What does the buggy code output?"
              value={outputs[idx]}
              onChange={(e) => {
                const next = [...outputs];
                next[idx] = e.target.value;
                setOutputs(next);
              }}
            />
          </div>
        </div>
      ))}

      {error && <div className="error-banner">{error}</div>}

      {results && (
        <div style={{ marginTop: 16 }}>
          {results.results.map((r, idx) => (
            <div className="result-item" key={idx}>
              {r.call} — you said: {r.student_output}
              {r.error ? (
                <span className="result-badge incorrect">ERROR</span>
              ) : (
                <span className={`result-badge ${r.matches_actual ? "correct" : "incorrect"}`}>
                  {r.matches_actual ? "MATCHES ACTUAL" : `ACTUAL: ${r.actual_buggy_output}`}
                </span>
              )}
            </div>
          ))}
          <div className="success-banner">Great — moving on to the final step.</div>
        </div>
      )}

      {!results && (
        <button onClick={handleSubmit} disabled={loading}>
          {loading ? "Checking..." : "Submit trace"}
        </button>
      )}
    </div>
  );
}
