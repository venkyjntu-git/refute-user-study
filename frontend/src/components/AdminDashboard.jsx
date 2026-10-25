import React, { useCallback, useEffect, useState } from "react";
import { adminApi, adminToken, AuthError } from "../api";

// Research dashboard: descriptive results along the paper's RQs, the
// per-session responses, and the CSV exports. Reached at ?mode=admin and
// guarded server-side (every /api/admin/* call needs the bearer token).

const FORM_LABEL = { direct: "Direct", contextualized: "Contextualized" };

const fmtRate = (r) =>
  !r || !r.n ? "—" : `${r.k}/${r.n} (${r.pct}%)`;
const fmtNum = (v, unit = "") => (v === null || v === undefined ? "—" : `${v}${unit}`);
const fmtSecs = (v) => fmtNum(v, " s");
const fmtPp = (v) => (v === null || v === undefined ? "—" : `${v > 0 ? "+" : ""}${v} pp`);

function Table({ columns, rows, rowKey }) {
  return (
    <div className="table-scroll">
      <table className="admin-table">
        <thead>
          <tr>{columns.map((c) => <th key={c.label}>{c.label}</th>)}</tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr><td colSpan={columns.length} className="admin-empty">No data yet.</td></tr>
          )}
          {rows.map((row, i) => (
            <tr key={rowKey ? rowKey(row) : i}>
              {columns.map((c) => <td key={c.label}>{c.render(row)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function Section({ title, note, children }) {
  return (
    <section className="admin-section">
      <h3>{title}</h3>
      {note && <p className="admin-note">{note}</p>}
      {children}
    </section>
  );
}

function Login({ onLoggedIn }) {
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const res = await adminApi.login(password);
      adminToken.set(res.token);
      onLoggedIn();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="card" onSubmit={submit}>
      <h1>Study admin</h1>
      <label htmlFor="admin-password">Admin password</label>
      <input
        id="admin-password"
        type="password"
        className="admin-password"
        value={password}
        autoComplete="current-password"
        onChange={(e) => setPassword(e.target.value)}
      />
      {error && <div className="error-banner">{error}</div>}
      <button type="submit" disabled={loading || !password}>
        {loading ? "Checking..." : "Log in"}
      </button>
    </form>
  );
}

const finishCols = [
  { label: "Finished", render: (r) => r.finished },
  { label: "Refuted", render: (r) => fmtRate(r.success) },
  { label: "Refuted on 1st attempt", render: (r) => fmtRate(r.first_attempt_success) },
  { label: "Right input, wrong outputs", render: (r) => fmtRate(r.found_input_but_wrong_outputs) },
  { label: "Median Step 1 time", render: (r) => fmtSecs(r.median_s1_seconds) },
  { label: "Median Step 3 time", render: (r) => fmtSecs(r.median_s3_seconds) },
];

function Results({ a }) {
  const o = a.overview;
  return (
    <>
      <div className="stat-row">
        <div className="stat"><span>{o.participants}</span>participants</div>
        <div className="stat"><span>{o.participants_complete}</span>finished both problems</div>
        <div className="stat"><span>{o.sessions_finished}/{o.sessions}</span>problems finished</div>
        <div className="stat">
          <span>{Object.keys(o.by_institute).length}</span>
          {Object.entries(o.by_institute).map(([k, v]) => `${k}: ${v}`).join(" · ") || "institutes"}
        </div>
      </div>

      <Section
        title="RQ1 · Correctness by form"
        note="Refuted = valid input with both outputs right, within the attempt limit. Rates are over finished problems."
      >
        <Table
          columns={[{ label: "Form", render: (r) => FORM_LABEL[r.form] }, ...finishCols]}
          rows={a.by_form}
          rowKey={(r) => r.form}
        />
      </Section>

      <Section
        title="RQ2 · Form × kind of bug"
        note="If context only adds reading load, Contextualized should not beat Direct for either bug. If it also aids comprehension, it should help Buggy2 more than Buggy1."
      >
        <Table
          columns={[
            { label: "Bug", render: (r) => r.bug_label },
            { label: "Form", render: (r) => FORM_LABEL[r.form] },
            ...finishCols,
          ]}
          rows={a.form_bug}
          rowKey={(r) => `${r.bug}-${r.form}`}
        />
        <div className="effect-row">
          <div>Context effect on Buggy1 (Contextualized − Direct): <strong>{fmtPp(a.context_effect_pp.buggy1)}</strong></div>
          <div>Context effect on Buggy2 (Contextualized − Direct): <strong>{fmtPp(a.context_effect_pp.buggy2)}</strong></div>
          <div>Benefit of context (Buggy2 effect − Buggy1 effect): <strong>{fmtPp(a.context_benefit_pp)}</strong></div>
        </div>
      </Section>

      <Section
        title="Same student, both forms"
        note="Each participant did one problem in each form. Counts over participants who finished both."
      >
        <Table
          columns={[
            { label: "Group", render: (r) => r.group },
            { label: "Participants", render: (r) => r.participants },
            { label: "Correct in both", render: (r) => r.both_correct },
            { label: "Direct only", render: (r) => r.direct_only },
            { label: "Contextualized only", render: (r) => r.contextualized_only },
            { label: "Neither", render: (r) => r.neither },
          ]}
          rows={a.paired}
          rowKey={(r) => r.group}
        />
      </Section>

      <Section title="Step 1 · Understanding the task" note="Input–output pairs, checked against the reference solution.">
        <Table
          columns={[
            { label: "Form", render: (r) => FORM_LABEL[r.form] },
            { label: "Sessions", render: (r) => r.sessions },
            { label: "Failed 1st attempt", render: (r) => fmtRate(r.failed_first_attempt) },
            { label: "Mean attempts", render: (r) => fmtNum(r.mean_attempts) },
            { label: "Asked for examples", render: (r) => fmtRate(r.requested_examples) },
            { label: "Never passed", render: (r) => fmtRate(r.never_passed) },
            { label: "Median time", render: (r) => fmtSecs(r.median_seconds) },
          ]}
          rows={a.step1}
          rowKey={(r) => r.form}
        />
        <p className="admin-note">A counter-example was already among the student's own Step 1 pairs:</p>
        <Table
          columns={[
            { label: "Bug", render: (r) => r.bug_label },
            { label: "Form", render: (r) => FORM_LABEL[r.form] },
            { label: "Had a counter-example in Step 1", render: (r) => fmtRate(r.already_had_counterexample) },
          ]}
          rows={a.step1_counterexamples}
          rowKey={(r) => `${r.bug}-${r.form}`}
        />
      </Section>

      <Section
        title="Step 2 · Tracing the code"
        note="Code and inputs are identical under both forms, so these should not differ — a check, not a result."
      >
        <Table
          columns={[
            { label: "Form", render: (r) => FORM_LABEL[r.form] },
            { label: "Sessions", render: (r) => r.sessions },
            { label: "Mean cell accuracy", render: (r) => fmtNum(r.mean_cell_accuracy_pct, "%") },
            { label: "Fully correct trace", render: (r) => fmtRate(r.fully_correct) },
            { label: "Buggy line traced right", render: (r) => fmtRate(r.correct_at_buggy_line) },
            { label: "Median time", render: (r) => fmtSecs(r.median_seconds) },
          ]}
          rows={a.step2}
          rowKey={(r) => r.form}
        />
      </Section>

      <Section
        title="Step 3 among students who understood the task and traced the code"
        note="Only sessions with Step 1 right on the first attempt and a fully correct Step 2 trace."
      >
        <Table
          columns={[
            { label: "Bug", render: (r) => r.bug_label },
            { label: "Form", render: (r) => FORM_LABEL[r.form] },
            ...finishCols.slice(0, 3),
          ]}
          rows={a.conditional}
          rowKey={(r) => `${r.bug}-${r.form}`}
        />
      </Section>

      <Section
        title="Where failed refutations came from"
        note="Each finished-but-not-refuted problem, traced back to the first step that went wrong."
      >
        <Table
          columns={[
            { label: "Form", render: (r) => FORM_LABEL[r.form] },
            { label: "Failed", render: (r) => r.failed },
            { label: "Misread the task (Step 1)", render: (r) => fmtRate(r.task_misread) },
            { label: "Mis-traced the code (Step 2)", render: (r) => fmtRate(r.code_mistraced) },
            { label: "Understood both", render: (r) => fmtRate(r.understood_both) },
            { label: "Found the input, wrong outputs", render: (r) => fmtRate(r.found_input_wrong_outputs) },
            { label: "Invalid / implausible attempts", render: (r) => r.invalid_or_implausible_attempts },
          ]}
          rows={a.failures}
          rowKey={(r) => r.form}
        />
      </Section>

      <Section title="RQ3 · Use of the code-mixed specification">
        <Table
          columns={[
            { label: "Form", render: (r) => FORM_LABEL[r.form] },
            { label: "Sessions", render: (r) => r.sessions },
            { label: "Switched to code-mixed", render: (r) => fmtRate(r.switched) },
            { label: "Mean switches", render: (r) => fmtNum(r.mean_switches) },
            { label: "Median time to first switch", render: (r) => fmtSecs(r.median_seconds_to_first_switch) },
          ]}
          rows={a.switching}
          rowKey={(r) => r.form}
        />
        <Table
          columns={[
            { label: "Native language", render: (r) => r.native_language },
            { label: "Sessions", render: (r) => r.sessions },
            { label: "Switched", render: (r) => fmtRate(r.switched) },
          ]}
          rows={a.switching_by_language}
          rowKey={(r) => r.native_language}
        />
      </Section>

      <Section title="By self-rated English reading" note="Students who switch differ from those who don't, so these are descriptive only.">
        <Table
          columns={[
            { label: "Reading", render: (r) => r.band },
            { label: "Form", render: (r) => FORM_LABEL[r.form] },
            { label: "Sessions", render: (r) => r.sessions },
            { label: "Step 1 right 1st time", render: (r) => fmtRate(r.step1_first_attempt_correct) },
            { label: "Switched", render: (r) => fmtRate(r.switched) },
            { label: "Refuted", render: (r) => fmtRate(r.success) },
            { label: "Median Step 1 time", render: (r) => fmtSecs(r.median_s1_seconds) },
          ]}
          rows={a.proficiency}
          rowKey={(r) => `${r.band}-${r.form}`}
        />
      </Section>

      <Section title="Per variant">
        <Table
          columns={[
            { label: "Variant", render: (r) => r.variant },
            { label: "Sessions", render: (r) => r.sessions },
            ...finishCols,
          ]}
          rows={a.variants}
          rowKey={(r) => r.variant}
        />
      </Section>
    </>
  );
}

const yes = (v) => (v ? "✓" : "✗");

function Responses({ rows }) {
  const [open, setOpen] = useState(null);
  return (
    <Section title={`Responses (${rows.length} sessions)`} note="One row per participant × problem. Click a row for the Step 3 inputs and explanations.">
      <div className="table-scroll">
        <table className="admin-table">
          <thead>
            <tr>
              <th>Student</th><th>Institute</th><th>#</th><th>Variant</th><th>Lang</th><th>Eng.</th>
              <th>S1 tries</th><th>S1 1st ok</th><th>S2 acc.</th><th>S3 tries</th><th>Refuted</th><th>Mixed</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && <tr><td colSpan={12} className="admin-empty">No responses yet.</td></tr>}
            {rows.map((r) => (
              <React.Fragment key={r.session_id}>
                <tr className="clickable" onClick={() => setOpen(open === r.session_id ? null : r.session_id)}>
                  <td>{r.student_identifier}</td>
                  <td>{r.institute}</td>
                  <td>{r.position}</td>
                  <td>{r.variant}</td>
                  <td>{r.native_language}</td>
                  <td>{fmtNum(r.english_proficiency)}</td>
                  <td>{r.s1_attempts}</td>
                  <td>{yes(r.s1_first_correct)}</td>
                  <td>{fmtNum(r.s2_cell_accuracy, "%")}</td>
                  <td>{r.s3_attempts}</td>
                  <td>{r.s3_closed ? yes(r.s3_success) : "…"}</td>
                  <td>{r.switched_to_mixed ? `✓ (${r.spec_switches})` : ""}</td>
                </tr>
                {open === r.session_id && (
                  <tr className="detail-row">
                    <td colSpan={12}>
                      <div><strong>Step 3 inputs:</strong> {r.s3_inputs.length ? r.s3_inputs.join("  ·  ") : "—"}</div>
                      <div><strong>How they found it:</strong> {r.s3_how_found.length ? r.s3_how_found.join("  ·  ") : "—"}</div>
                      <div>
                        <strong>Times:</strong> Step 1 {fmtSecs(r.s1_seconds)}, Step 2 {fmtSecs(r.s2_seconds)}, Step 3 {fmtSecs(r.s3_seconds)}
                        {" · "}Step 1 already had a counter-example: {yes(r.s1_counterexample_in_pairs)}
                        {" · "}Invalid/implausible Step 3 attempts: {r.s3_invalid_attempts}
                      </div>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      </div>
    </Section>
  );
}

const DOWNLOADS = [
  { path: "/api/admin/session_summary.csv", file: "session_summary.csv",
    what: "One row per participant × problem with every measure on this dashboard." },
  { path: "/api/admin/export.csv", file: "study_export.csv",
    what: "Every logged event (shown / submitted) with its full payload." },
  { path: "/api/admin/spec_view_export.csv", file: "spec_views.csv",
    what: "Every English / code-mixed view and switch, with timestamps." },
  { path: "/api/admin/trace_export.csv", file: "trace_cells.csv",
    what: "Step 2 control-flow answers, one row per line." },
  { path: "/api/admin/data_flow_export.csv", file: "data_flow_cells.csv",
    what: "Step 2 data-flow answers, one row per variable value." },
];

function Downloads({ institute, onError }) {
  const [busy, setBusy] = useState(null);
  const get = async (d) => {
    setBusy(d.path);
    try {
      // Only the session summary is filtered by institute server-side.
      const path = d.path.endsWith("session_summary.csv") && institute
        ? `${d.path}?institute=${encodeURIComponent(institute)}` : d.path;
      await adminApi.download(path, d.file);
    } catch (e) {
      onError(e);
    } finally {
      setBusy(null);
    }
  };
  return (
    <Section title="Downloads">
      {DOWNLOADS.map((d) => (
        <div className="download-row" key={d.path}>
          <button className="secondary" onClick={() => get(d)} disabled={busy === d.path}>
            {busy === d.path ? "Downloading..." : d.file}
          </button>
          <span>{d.what}</span>
        </div>
      ))}
    </Section>
  );
}

export default function AdminDashboard() {
  const [loggedIn, setLoggedIn] = useState(Boolean(adminToken.get()));
  const [tab, setTab] = useState("results");
  const [institute, setInstitute] = useState("");
  const [institutes, setInstitutes] = useState([]);
  const [analysis, setAnalysis] = useState(null);
  const [responses, setResponses] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleError = useCallback((e) => {
    if (e instanceof AuthError) setLoggedIn(false);
    setError(e.message);
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [a, r, inst] = await Promise.all([
        adminApi.analysis(institute), adminApi.responses(institute), adminApi.institutes(),
      ]);
      setAnalysis(a);
      setResponses(r);
      setInstitutes(inst);
    } catch (e) {
      handleError(e);
    } finally {
      setLoading(false);
    }
  }, [institute, handleError]);

  useEffect(() => {
    if (loggedIn) load();
  }, [loggedIn, load]);

  if (!loggedIn) {
    return (
      <>
        {error && <div className="error-banner">{error}</div>}
        <Login onLoggedIn={() => { setError(null); setLoggedIn(true); }} />
      </>
    );
  }

  return (
    <div className="card admin">
      <div className="admin-header">
        <h1>Study results</h1>
        <div className="admin-controls">
          <select value={institute} onChange={(e) => setInstitute(e.target.value)} aria-label="Institute filter">
            <option value="">All institutes</option>
            {institutes.map((i) => <option key={i} value={i}>{i}</option>)}
          </select>
          <button className="secondary" onClick={load} disabled={loading}>
            {loading ? "Loading..." : "Refresh"}
          </button>
          <button className="secondary" onClick={() => { adminToken.clear(); setLoggedIn(false); }}>
            Log out
          </button>
        </div>
      </div>

      <div className="admin-tabs" role="tablist">
        {[["results", "Results"], ["responses", "Responses"], ["downloads", "Downloads"]].map(([k, label]) => (
          <button
            key={k}
            role="tab"
            aria-selected={tab === k}
            className={tab === k ? "active" : ""}
            onClick={() => setTab(k)}
          >
            {label}
          </button>
        ))}
      </div>

      {error && <div className="error-banner">{error}</div>}
      {tab === "results" && analysis && <Results a={analysis} />}
      {tab === "responses" && <Responses rows={responses} />}
      {tab === "downloads" && <Downloads institute={institute} onError={handleError} />}
    </div>
  );
}
