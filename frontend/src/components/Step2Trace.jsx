import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api";

// Line numbers here must line up with the trace table's row numbers, which
// are 1-based indices into this same source (backend/sandbox.py reads
// lineno straight off code.splitlines(), no dedent) — so the numbering
// can't drift from theirs.
function numberedCode(code) {
  const lines = code.replace(/\n$/, "").split("\n");
  const width = String(lines.length).length;
  return lines.map((line, i) => `${String(i + 1).padStart(width)}  ${line}`).join("\n");
}

// Non-prefilled rows start with an empty count ("" — unanswered, distinct
// from an explicit "0"). The control-flow table asks ONLY this count — no
// variable values at all, that's the data-flow table's job over a
// different sample input (see trace_table.py's module docstring).
function blankAnswers(tables) {
  return tables.map((table) => ({
    rows: table.rows.map((row) => ({ count: row.prefilled ? String(row.count) : "" })),
    final_output: "",
  }));
}

// Data-flow tables are much simpler than the control-flow ones: the true
// execution skeleton (which rows exist, in which order) is given outright,
// so there's no count to answer — just one set of variable cells per given
// row, exactly like the very first (pre-leak-fix) trace table design. Safe
// here because a data-flow table is always built for a different sample
// input than the control-flow question.
function blankDataFlowAnswers(tables) {
  return tables.map((table) => ({
    rows: table.rows.map((row) => ({
      vars: Object.fromEntries(
        Object.keys(row.vars).map((name) => [name, row.prefilled ? row.vars[name] : ""])
      ),
    })),
    final_output: "",
  }));
}

export default function Step2Trace({ session, buggyCode, traceTables, dataFlowTables, onCompleted }) {
  const tables = useMemo(() => traceTables || [], [traceTables]);
  const dfTables = useMemo(() => dataFlowTables || [], [dataFlowTables]);
  const [answers, setAnswers] = useState(() => blankAnswers(tables));
  const [dfAnswers, setDfAnswers] = useState(() => blankDataFlowAnswers(dfTables));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.markShown(session.session_id, "buggy_trace").catch(() => {});
  }, [session.session_id]);

  const setCount = (t, r, value) => {
    setAnswers((prev) => {
      const next = prev.map((a) => ({ ...a, rows: a.rows.map((row) => ({ ...row })) }));
      next[t].rows[r].count = value;
      return next;
    });
  };

  const setFinal = (t, value) => {
    setAnswers((prev) => {
      const next = prev.map((a) => ({ ...a, rows: a.rows.map((row) => ({ ...row })) }));
      next[t].final_output = value;
      return next;
    });
  };

  const setDfCell = (t, r, name, value) => {
    setDfAnswers((prev) => {
      const next = prev.map((a) => ({ ...a, rows: a.rows.map((row) => ({ ...row, vars: { ...row.vars } })) }));
      next[t].rows[r].vars[name] = value;
      return next;
    });
  };

  const setDfFinal = (t, value) => {
    setDfAnswers((prev) => {
      const next = prev.map((a) => ({ ...a, rows: a.rows.map((row) => ({ ...row, vars: { ...row.vars } })) }));
      next[t].final_output = value;
      return next;
    });
  };

  const firstEmpty = () => {
    for (let t = 0; t < tables.length; t += 1) {
      const table = tables[t];
      for (let r = 0; r < table.rows.length; r += 1) {
        if (table.rows[r].prefilled) continue;
        const raw = answers[t].rows[r].count;
        const parsed = parseInt(raw, 10);
        if (raw.trim() === "" || isNaN(parsed) || parsed < 0) {
          return `${table.call}, line ${table.rows[r].lineno}: how many times does this line run?`;
        }
      }
      if (!answers[t].final_output.trim()) return `${table.call}: return value`;
    }
    for (let t = 0; t < dfTables.length; t += 1) {
      // Data-flow tables have no count to answer (the skeleton is given) and
      // no forced value cells (blank is fine, and unscored) — only the
      // return-value box is required.
      if (!dfAnswers[t].final_output.trim()) return `${dfTables[t].call}: return value`;
    }
    return null;
  };

  const handleSubmit = async () => {
    const missing = firstEmpty();
    if (missing) {
      setError(`Please answer every row before submitting — missing ${missing}.`);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const traces = tables.map((table, t) => ({
        call: table.call,
        rows: table.rows
          .map((row, r) => ({ row, answer: answers[t].rows[r] }))
          .filter(({ row }) => !row.prefilled)
          .map(({ row, answer }) => ({
            lineno: row.lineno,
            count: parseInt(answer.count, 10),
          })),
        final_output: answers[t].final_output,
      }));
      const dataFlowTraces = dfTables.map((table, t) => ({
        call: table.call,
        rows: table.rows
          .map((row, r) => ({ row, answer: dfAnswers[t].rows[r] }))
          .filter(({ row }) => !row.prefilled)
          .map(({ row, answer }) => ({
            step: row.step,
            vars: Object.fromEntries(
              Object.entries(answer.vars).filter(([, v]) => v.trim() !== "")
            ),
          })),
        final_output: dfAnswers[t].final_output,
      }));
      await api.submitTraces(session.session_id, traces, dataFlowTraces);
      onCompleted();
    } catch (e) {
      setError(e.message);
      setLoading(false);
    }
  };

  return (
    <div className="card">
      <h2>Step 2: Trace the buggy code</h2>
      <p>
        Here is the buggy implementation. For each sample input below, every
        line of the function is listed. Say <strong>how many times</strong>{" "}
        each line runs for that call (0 if it never runs). The first row is
        filled in for you as an example.
      </p>
      <p className="notice">
        You get <strong>one attempt</strong>, and you will not be told whether
        your answers were right — just do your best and move on.
      </p>
      <pre className="code-block">{numberedCode(buggyCode)}</pre>

      {tables.map((table, t) => (
        <div key={table.call} className="trace-block">
          {/* Only distinguish "control flow" from a plain "Trace" heading
              once there's a data-flow section to contrast it with — a task
              with no trace_data_flow_inputs shouldn't introduce unexplained
              jargon for a single, ordinary trace table. */}
          <h3>{dfTables.length > 0 ? "Control flow" : "Trace"}: <code>{table.call}</code></h3>
          {table.error ? (
            <div className="error-banner">
              This trace could not be prepared: {table.error}
            </div>
          ) : (
            <>
              {table.truncated && (
                <p className="notice">
                  This trace is long, so only the first part of the execution is
                  shown.
                </p>
              )}
              <div className="table-scroll">
                <table className="trace-table">
                  <thead>
                    <tr>
                      <th>Line</th>
                      <th>Times?</th>
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.map((row, r) => (
                      <tr key={row.lineno} className={row.prefilled ? "prefilled" : ""}>
                        <td>
                          <code>{row.lineno}: {row.line_text}</code>
                        </td>
                        <td>
                          {row.prefilled ? (
                            <code>{row.count}</code>
                          ) : (
                            <input
                              type="number" min="0" step="1"
                              aria-label={`${table.call} line ${row.lineno} how many times does this run?`}
                              value={answers[t].rows[r].count}
                              onChange={(e) => setCount(t, r, e.target.value)}
                            />
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="trace-final">
                <label>What does <code>{table.call}</code> return?</label>
                <input
                  type="text"
                  value={answers[t].final_output}
                  onChange={(e) => setFinal(t, e.target.value)}
                />
              </div>
            </>
          )}
        </div>
      ))}

      {dfTables.length > 0 && (
        <>
          <h3 className="section-divider">Data flow</h3>
          <p>
            For the input(s) below, the execution path is given outright —
            every row that actually runs is already listed, in order. Just
            fill in the value of each variable <em>after</em> that line has
            finished.
          </p>
        </>
      )}

      {dfTables.map((table, t) => (
        <div key={table.call} className="trace-block">
          <h3>Data flow: <code>{table.call}</code></h3>
          {table.error ? (
            <div className="error-banner">
              This trace could not be prepared: {table.error}
            </div>
          ) : (
            <>
              {table.truncated && (
                <p className="notice">
                  This trace is long, so only the first part of the execution is
                  shown.
                </p>
              )}
              <div className="table-scroll">
                <table className="trace-table">
                  <thead>
                    <tr>
                      <th>Step</th>
                      <th>Line</th>
                      {table.var_names.map((name) => (
                        <th key={name}><code>{name}</code></th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.map((row, r) => (
                      <tr key={row.step} className={row.prefilled ? "prefilled" : ""}>
                        <td>{row.step}</td>
                        <td>
                          <code>{row.lineno}: {row.line_text}</code>
                        </td>
                        {table.var_names.map((name) => (
                          <td key={name}>
                            {!(name in row.vars) ? (
                              <span className="not-in-scope">—</span>
                            ) : row.prefilled ? (
                              <code>{row.vars[name]}</code>
                            ) : (
                              <input
                                type="text"
                                aria-label={`${table.call} step ${row.step} value of ${name}`}
                                value={dfAnswers[t].rows[r].vars[name]}
                                onChange={(e) => setDfCell(t, r, name, e.target.value)}
                              />
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="trace-final">
                <label>What does <code>{table.call}</code> return?</label>
                <input
                  type="text"
                  value={dfAnswers[t].final_output}
                  onChange={(e) => setDfFinal(t, e.target.value)}
                />
              </div>
            </>
          )}
        </div>
      ))}

      {error && <div className="error-banner">{error}</div>}

      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Submitting..." : "Submit trace"}
      </button>
    </div>
  );
}
