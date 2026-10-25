import React, { useState } from "react";
import { api } from "../api";

// Fixed lists rather than free text, so values are consistent across entries
// in the exported data.
const INSTITUTES = ["BITS Goa", "JNTUGV", "IITRAM", "PSG iTech", "DHAW", "Ashoka"];

// `value` is the key the backend looks up in Task.description_mixed (see
// backend/seed_study.py) — a language with no code-mixed text for a task
// simply gets no toggle.
export const NATIVE_LANGUAGES = [
  { value: "te", label: "Telugu" },
  { value: "ta", label: "Tamil" },
  { value: "hi", label: "Hindi" },
  { value: "gu", label: "Gujarati" },
  { value: "de", label: "German" },
];

const SCHOOLING_MEDIUMS = [
  "English",
  "My native language",
  "Partly English, partly my native language",
  "Other",
];

const PROFICIENCY = [
  { value: 1, label: "1 — I find reading English very difficult" },
  { value: 2, label: "2" },
  { value: 3, label: "3" },
  { value: 4, label: "4" },
  { value: 5, label: "5 — I read English easily" },
];

// Entry point for the counterbalanced study: identity plus the short survey.
// The server assigns (or, for a returning student, restores) which two
// problems they get and in which form — nothing here chooses a task.
export default function StudyIntro({ onRegistered }) {
  const [studentId, setStudentId] = useState("");
  const [institute, setInstitute] = useState("");
  const [nativeLanguage, setNativeLanguage] = useState("");
  const [schoolingMedium, setSchoolingMedium] = useState("");
  const [proficiency, setProficiency] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleStart = async () => {
    if (!institute) return setError("Please select an institute.");
    if (!studentId.trim()) return setError("Please enter a participant / student identifier.");
    if (!nativeLanguage) return setError("Please select your native language.");
    if (!schoolingMedium) return setError("Please select the medium of your schooling.");
    if (!proficiency) return setError("Please rate your English reading.");
    setLoading(true);
    setError(null);
    try {
      const res = await api.registerParticipant({
        student_identifier: studentId.trim(),
        institute,
        native_language: nativeLanguage,
        schooling_medium: schoolingMedium,
        english_proficiency: Number(proficiency),
      });
      await onRegistered(res);
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
        You will work on two problems. For each one you'll read a task
        description and give sample input/output pairs, trace some code, then
        find an input that shows the code is wrong.
      </p>

      <label>Institute</label>
      <select value={institute} onChange={(e) => setInstitute(e.target.value)}>
        <option value="" disabled>Select institute…</option>
        {INSTITUTES.map((name) => <option key={name} value={name}>{name}</option>)}
      </select>

      <label>Participant / Student ID</label>
      <input
        type="text"
        value={studentId}
        onChange={(e) => setStudentId(e.target.value)}
        placeholder="e.g. P014"
      />

      <label>Your native language</label>
      <select value={nativeLanguage} onChange={(e) => setNativeLanguage(e.target.value)}>
        <option value="" disabled>Select language…</option>
        {NATIVE_LANGUAGES.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
      </select>

      <label>Medium of instruction at school</label>
      <select value={schoolingMedium} onChange={(e) => setSchoolingMedium(e.target.value)}>
        <option value="" disabled>Select…</option>
        {SCHOOLING_MEDIUMS.map((m) => <option key={m} value={m}>{m}</option>)}
      </select>

      <label>How easily do you read English?</label>
      <select value={proficiency} onChange={(e) => setProficiency(e.target.value)}>
        <option value="" disabled>Select…</option>
        {PROFICIENCY.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
      </select>

      {error && <div className="error-banner">{error}</div>}
      <button onClick={handleStart} disabled={loading}>
        {loading ? "Starting..." : "Start"}
      </button>
    </div>
  );
}
