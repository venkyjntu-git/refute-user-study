import React, { useState } from "react";
import { api } from "../api";

// Fixed list rather than free text, so institute names are consistent across
// entries in the exported data (no "BITS Goa" vs "Bits goa" vs "bits-goa").
const INSTITUTES = ["Ashoka", "JNTUGV", "BITS Goa", "X", "Y", "Z"];

// Value is what the backend's `language` column stores (see models.Task);
// label is just display text. Only "python" has a working execution engine
// today — see sandbox.py — but all three are offered so the study runner can
// seed C/OCaml tasks and switch this on per language as each one lands.
const LANGUAGES = [
  { value: "python", label: "Python" },
  { value: "c", label: "C" },
  { value: "ocaml", label: "OCaml" },
];

export default function TaskIntro({ onStarted }) {
  const [studentId, setStudentId] = useState("");
  const [institute, setInstitute] = useState("");
  const [language, setLanguage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleStart = async () => {
    if (!studentId.trim()) {
      setError("Please enter a participant / student identifier.");
      return;
    }
    if (!institute) {
      setError("Please select an institute.");
      return;
    }
    if (!language) {
      setError("Please select a language.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      // Backend loads the first task authored for the chosen language —
      // there's no task-id picker here by design; see schemas.StartSessionRequest.
      const session = await api.startSession(studentId.trim(), institute, language);
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
      <label>Institute</label>
      <select value={institute} onChange={(e) => setInstitute(e.target.value)}>
        <option value="" disabled>Select institute…</option>
        {INSTITUTES.map((name) => (
          <option key={name} value={name}>{name}</option>
        ))}
      </select>

      <label>Participant / Student ID</label>
      <input
        type="text"
        value={studentId}
        onChange={(e) => setStudentId(e.target.value)}
        placeholder="e.g. P014"
      />

      <label>Language</label>
      <select value={language} onChange={(e) => setLanguage(e.target.value)}>
        <option value="" disabled>Select language…</option>
        {LANGUAGES.map((lang) => (
          <option key={lang.value} value={lang.value}>{lang.label}</option>
        ))}
      </select>

      {error && <div className="error-banner">{error}</div>}
      <button onClick={handleStart} disabled={loading}>
        {loading ? "Starting..." : "Start"}
      </button>
    </div>
  );
}
