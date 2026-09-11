import React, { useEffect, useState } from "react";
import { api } from "../api";
import { extractFunctionName } from "../utils";

export default function Step3CounterExample({ session, buggyCode }) {
  const [args, setArgs] = useState("");
  const [predictedCorrect, setPredictedCorrect] = useState("");
  const [predictedBuggy, setPredictedBuggy] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const funcName = extractFunctionName(session.function_signature);

  useEffect(() => {
    api.markShown(session.session_id, "counter_example").catch(() => {});
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
      <p>{session.description}</p>

      <h3>Buggy code</h3>
      <pre className="code-block">{buggyCode}</pre>

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
              predictions were right. Study task complete. Thank you!
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

      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Checking..." : "Submit counter-example"}
      </button>
    </div>
  );
}
