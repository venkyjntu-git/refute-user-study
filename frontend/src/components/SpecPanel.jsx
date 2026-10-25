import React, { useEffect, useRef, useState } from "react";
import { api } from "../api";

// The task specification, with an optional English / code-mixed toggle.
// Each step starts in English; the first view and every switch are logged
// (study sessions only) — whether and when a student switches is itself a
// measure (RQ3). With no code-mixed text for this student, no toggle.
export default function SpecPanel({ session, step }) {
  const [version, setVersion] = useState("en");
  const hasMixed = Boolean(session.description_mixed);
  const logged = Boolean(session.participant_id);
  // StrictMode runs effects twice in development; log the first view once.
  const loggedViewFor = useRef(null);

  useEffect(() => {
    setVersion("en");
    const key = `${session.session_id}:${step}`;
    if (logged && loggedViewFor.current !== key) {
      loggedViewFor.current = key;
      api.logSpecView(session.session_id, step, "en").catch(() => {});
    }
  }, [session.session_id, step, logged]);

  const switchTo = (next) => {
    if (next === version) return;
    setVersion(next);
    if (logged) api.logSpecView(session.session_id, step, next).catch(() => {});
  };

  return (
    <div className="spec-panel">
      {hasMixed && (
        <div className="spec-toggle" role="group" aria-label="Specification language">
          <button
            type="button"
            className={version === "en" ? "active" : ""}
            aria-pressed={version === "en"}
            onClick={() => switchTo("en")}
          >
            English
          </button>
          <button
            type="button"
            className={version === "mixed" ? "active" : ""}
            aria-pressed={version === "mixed"}
            onClick={() => switchTo("mixed")}
          >
            Code-mixed
          </button>
        </div>
      )}
      <p className="spec-text">
        {version === "mixed" && hasMixed ? session.description_mixed : session.description}
      </p>
    </div>
  );
}
