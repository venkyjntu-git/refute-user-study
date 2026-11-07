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

// Shared by the three self-rated proficiency questions (1=novice 5=expert).
const PROFICIENCY = [
  { value: 1, label: "1 — novice" },
  { value: 2, label: "2" },
  { value: 3, label: "3" },
  { value: 4, label: "4" },
  { value: 5, label: "5 — expert" },
];

// `value` is what the backend stores (schemas.RegisterParticipantRequest).
const GENDERS = [
  { value: "Female", label: "Female" },
  { value: "Male", label: "Male" },
  { value: "Other", label: "Other" },
  { value: "NoResponse", label: "Prefer not to say" },
];

function ProficiencySelect({ id, label, value, onChange }) {
  return (
    <>
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        <option value="" disabled>Select…</option>
        {PROFICIENCY.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
      </select>
    </>
  );
}

// A whole number within [min, max], or null.
const wholeNumber = (s, min, max) => {
  if (!/^\d+$/.test(String(s).trim())) return null;
  const n = Number(s);
  return n >= min && n <= max ? n : null;
};

// Entry point for the counterbalanced study: identity plus the short survey.
// The server assigns (or, for a returning student, restores) which two
// problems they get and in which form — nothing here chooses a task.
export default function StudyIntro({ onRegistered }) {
  const [studentId, setStudentId] = useState("");
  const [institute, setInstitute] = useState("");
  const [nativeLanguage, setNativeLanguage] = useState("");
  const [schoolingMedium, setSchoolingMedium] = useState("");
  const [englishProficiency, setEnglishProficiency] = useState("");
  const [motherProficiency, setMotherProficiency] = useState("");
  const [programmingProficiency, setProgrammingProficiency] = useState("");
  const [courses, setCourses] = useState("");
  const [age, setAge] = useState("");
  const [gender, setGender] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleStart = async () => {
    if (!institute) return setError("Please select an institute.");
    if (!studentId.trim()) return setError("Please enter a participant / student identifier.");
    if (!nativeLanguage) return setError("Please select your native language.");
    if (!schoolingMedium) return setError("Please select the medium of your schooling.");
    if (!englishProficiency) return setError("Please rate your proficiency in English.");
    if (!motherProficiency) return setError("Please rate your proficiency in your mother language.");
    if (!programmingProficiency) return setError("Please rate your proficiency in computer programming.");
    const coursesN = wholeNumber(courses, 0, 50);
    if (coursesN === null) return setError("Please enter how many programming courses you have taken (a whole number, 0 or more).");
    const ageN = wholeNumber(age, 10, 100);
    if (ageN === null) return setError("Please enter your age in years.");
    if (!gender) return setError("Please select a gender option (or “Prefer not to say”).");
    setLoading(true);
    setError(null);
    try {
      const res = await api.registerParticipant({
        student_identifier: studentId.trim(),
        institute,
        native_language: nativeLanguage,
        schooling_medium: schoolingMedium,
        english_proficiency: Number(englishProficiency),
        mother_language_proficiency: Number(motherProficiency),
        programming_proficiency: Number(programmingProficiency),
        programming_courses: coursesN,
        age: ageN,
        gender,
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

      <ProficiencySelect
        id="q-english" label="Proficiency in English (1 = novice, 5 = expert)"
        value={englishProficiency} onChange={setEnglishProficiency}
      />
      <ProficiencySelect
        id="q-mother" label="Proficiency in your mother language (1 = novice, 5 = expert)"
        value={motherProficiency} onChange={setMotherProficiency}
      />
      <ProficiencySelect
        id="q-programming" label="Proficiency in computer programming (1 = novice, 5 = expert)"
        value={programmingProficiency} onChange={setProgrammingProficiency}
      />

      <label htmlFor="q-courses">How many computer programming courses have you taken?</label>
      <input
        id="q-courses" type="number" min="0" max="50" step="1" inputMode="numeric"
        value={courses} onChange={(e) => setCourses(e.target.value)}
      />

      <label htmlFor="q-age">Age (years)</label>
      <input
        id="q-age" type="number" min="10" max="100" step="1" inputMode="numeric"
        value={age} onChange={(e) => setAge(e.target.value)}
      />

      <label htmlFor="q-gender">Gender</label>
      <select id="q-gender" value={gender} onChange={(e) => setGender(e.target.value)}>
        <option value="" disabled>Select…</option>
        {GENDERS.map((g) => <option key={g.value} value={g.value}>{g.label}</option>)}
      </select>

      {error && <div className="error-banner">{error}</div>}
      <button onClick={handleStart} disabled={loading}>
        {loading ? "Starting..." : "Start"}
      </button>
    </div>
  );
}
