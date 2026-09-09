import React, { useEffect, useState } from "react";
import { api } from "../api";

export default function Step3CounterExample({ session }) {
  const [call, setCall] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.markShown(session.session_id, "counter_example").catch(() => {});
  }, [session.session_id]);

  const handleSubmit = async () => {
    if (!call.trim()) {
      setError("Please enter a function call to test as your counter-example.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.submitCounterExample(session.session_id, call.trim());
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
      <p>
        Give one input for which the buggy code produces a <em>different</em>{" "}
        result than the correct code. This is your refutation.
      </p>
      <label>Counter-example call</label>
      <input
        type="text"
        placeholder="e.g. max_of_three(1, 3, 5)"
        value={call}
        onChange={(e) => setCall(e.target.value)}
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
                Correct code output: {result.correct_output}
                <br />
                Buggy code output: {result.buggy_output}
              </>
            )}
          </div>
          {result.is_counter_example ? (
            <div className="success-banner">
              Confirmed — this is a valid counter-example. The outputs differ.
              Study task complete. Thank you!
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
