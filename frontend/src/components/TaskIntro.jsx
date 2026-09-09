import React, { useState } from "react";
import { api } from "../api";

export default function TaskIntro({ onStarted }) {
  const [studentId, setStudentId] = useState("");
  const [taskId, setTaskId] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleStart = async () => {
    if (!studentId.trim()) {
      setError("Please enter a participant / student identifier.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const session = await api.startSession(studentId.trim(), Number(taskId));
      onStarted(session);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h1>Refute Problem — User Study</h1>
      <p>
        You'll be shown a task description, and asked to give sample
        input/output pairs, trace some buggy code, then find a counter-example
        that shows the buggy code is wrong.
      </p>
      <label>Participant / Student ID</label>
      <input
        type="text"
        value={studentId}
        onChange={(e) => setStudentId(e.target.value)}
        placeholder="e.g. P014"
      />
      <label>Task ID</label>
      <input
        type="text"
        value={taskId}
        onChange={(e) => setTaskId(e.target.value)}
      />
      {error && <div className="error-banner">{error}</div>}
      <button onClick={handleStart} disabled={loading}>
        {loading ? "Starting..." : "Start"}
      </button>
    </div>
  );
}
