import React, { useState } from "react";
import { api } from "../api";

// Mirrors the Google Form "Sign-up: Refute Problem Programming Study (Same
// Code, Different Contexts)". Contact details are stored on their own
// (backend models.SignUp), never linked to the study responses.
const INSTITUTES = ["IITRAM", "PSG iTech", "JNTU-GV", "DHAW"];
const LANGUAGES = ["Python", "C"];

const CONSENTS = [
  {
    key: "consent_signup_only",
    text: "I understand this is a sign-up only, and I will receive the full Participant Information Sheet and sign a consent form at the session.",
  },
  {
    key: "consent_voluntary",
    text: "I understand participation is voluntary and will not affect my grades or academic standing, and there is no payment or academic credit.",
  },
  {
    key: "consent_contact",
    text: "I agree to be contacted by the study team using the details above about this study only.",
  },
];

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

function RadioGroup({ name, options, value, onChange }) {
  return (
    <div className="choice-group">
      {options.map((o) => (
        <label key={o} className="choice">
          <input type="radio" name={name} value={o} checked={value === o}
                 onChange={() => onChange(o)} />
          {o}
        </label>
      ))}
    </div>
  );
}

export default function SignUpForm({ onDone }) {
  const [fullName, setFullName] = useState("");
  const [rollNumber, setRollNumber] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [institute, setInstitute] = useState("");
  const [programme, setProgramme] = useState("");
  const [language, setLanguage] = useState("");
  const [consents, setConsents] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [submitted, setSubmitted] = useState(false);

  const handleSubmit = async () => {
    if (!fullName.trim()) return setError("Please enter your full name.");
    if (!rollNumber.trim()) return setError("Please enter your roll number / enrollment number.");
    if (!EMAIL_RE.test(email.trim())) return setError("Please enter a valid email address.");
    if (!institute) return setError("Please select your institute / college.");
    if (!programme.trim()) return setError("Please enter your programme and branch.");
    if (!language) return setError("Please select the programming language you are currently enrolled in.");
    if (!CONSENTS.every((c) => consents[c.key])) return setError("Please tick all three statements to sign up.");
    setLoading(true);
    setError(null);
    try {
      await api.signUp({
        full_name: fullName.trim(),
        roll_number: rollNumber.trim(),
        email: email.trim(),
        phone: phone.trim() || null,
        institute,
        programme_branch: programme.trim(),
        programming_language: language,
        ...Object.fromEntries(CONSENTS.map((c) => [c.key, true])),
      });
      setSubmitted(true);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (submitted) {
    return (
      <div className="card">
        <h2>Thank you for signing up</h2>
        <p>
          The local study contact will email you the session details and the
          full Participant Information Sheet. Signing up does not oblige you to
          take part; you can withdraw at any time before or during the session.
        </p>
        <button onClick={onDone}>Continue to demo video</button>
      </div>
    );
  }

  return (
    <div className="card">
      <h1>Sign-up: Refute Problem Programming Study (Same Code, Different Contexts)</h1>
      <p>
        You are invited to take part in a research study on how task
        descriptions affect introductory programming students' understanding
        of buggy programs.
      </p>
      <p>
        <strong>What it involves:</strong> one supervised lab session of about
        60 minutes, where you attempt two programming tasks (read a
        specification, trace a buggy program, give an input that makes it
        fail). You may switch between English and an available local-language
        (Tamil, Telugu, German, Gujarati, Hindi) description.
      </p>
      <p>
        Participation is voluntary. Declining or stopping will not affect your
        grades, academic standing, or relationship with your institution or
        instructor. It is not a graded assessment. There is no payment or
        academic credit.
      </p>
      <p>
        This form is only for sign-up. Your contact details here are kept
        separately from your study responses. You will receive the full
        Participant Information Sheet and sign a written consent form at the
        session before anything is recorded.
      </p>
      <p><strong>Coordinators:</strong></p>
      <ol>
        <li>Nimisha Agarwal, Lecturer, IITRAM, Ahmedabad, India</li>
        <li>S. Sangeetha, PSG Institute of Technology and Applied Research, Coimbatore, India</li>
        <li>N. Venkatesh, JNTU-GV College of Engineering, Vizianagaram, Andhra Pradesh, India.</li>
        <li>Andreas Lingnau, German University of Applied Sciences (DHAW), Potsdam, Germany.</li>
      </ol>

      <h3 className="form-section">Eligibility</h3>
      <p>
        First Year Engineering Undergraduate Student / BSc Students who are
        studying the introductory programming courses.
      </p>

      <h3 className="form-section">Your details</h3>
      <p className="hint">We use these only to contact you about this study.</p>

      <label htmlFor="su-name">Full name *</label>
      <input id="su-name" type="text" value={fullName} onChange={(e) => setFullName(e.target.value)} />

      <label htmlFor="su-roll">Roll Number / Enrollment Number *</label>
      <input id="su-roll" type="text" value={rollNumber} onChange={(e) => setRollNumber(e.target.value)} />

      <label htmlFor="su-email">Email address (institutional email preferred) *</label>
      <input id="su-email" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />

      <label htmlFor="su-phone">Phone / WhatsApp number (optional)</label>
      <p className="hint">Only if you are happy to be contacted this way about scheduling.</p>
      <input id="su-phone" type="text" value={phone} onChange={(e) => setPhone(e.target.value)} />

      <label>Institute / college name *</label>
      <RadioGroup name="su-institute" options={INSTITUTES} value={institute} onChange={setInstitute} />

      <label htmlFor="su-programme">Programme and branch (e.g., B.Tech CSE) *</label>
      <input id="su-programme" type="text" value={programme} onChange={(e) => setProgramme(e.target.value)} />

      <label>Currently Enrolled Programming language *</label>
      <RadioGroup name="su-language" options={LANGUAGES} value={language} onChange={setLanguage} />

      <h3 className="form-section">Before you submit</h3>
      <p>
        <strong>Expected Benefits to Participants:</strong> Participants may
        gain a better understanding of programming. Finding a failing input
        for buggy code requires careful reading of the specification and
        careful tracing of the code, which may improve their logical thinking
        and debugging skills. The study may also help them become more aware
        of how the wording of a problem affects their understanding. The wider
        benefit is research that helps instructors design better programming
        assessments for learners from diverse language backgrounds.
      </p>
      <p><strong>Wage Compensation / Financial Benefits:</strong> No</p>

      <label>Please confirm all of the following *</label>
      <div className="choice-group">
        {CONSENTS.map((c) => (
          <label key={c.key} className="choice">
            <input
              type="checkbox" checked={!!consents[c.key]}
              onChange={(e) => setConsents({ ...consents, [c.key]: e.target.checked })}
            />
            {c.text}
          </label>
        ))}
      </div>

      {error && <div className="error-banner">{error}</div>}
      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Submitting..." : "Sign up"}
      </button>
    </div>
  );
}
