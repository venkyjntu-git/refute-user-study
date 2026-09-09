import React, { useEffect, useMemo, useState } from "react";
import { api } from "../api";

// Cells the student must fill start empty. A variable that is not in scope on
// a given row is absent from `row.vars` entirely and renders as an em dash —
// it is never asked, so it never counts against them.
function blankAnswers(tables) {
  return tables.map((table) => ({
    rows: table.rows.map((row) => {
      const vars = {};
      Object.keys(row.vars).forEach((name) => {
        vars[name] = row.prefilled ? row.vars[name] : "";
      });
      return { vars, next_line: row.prefilled ? row.next_line : "" };
    }),
    final_output: "",
  }));
}

export default function Step2Trace({ session, buggyCode, traceTables, onCompleted }) {
  const tables = useMemo(() => traceTables || [], [traceTables]);
  const [answers, setAnswers] = useState(() => blankAnswers(tables));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    api.markShown(session.session_id, "buggy_trace").catch(() => {});
  }, [session.session_id]);

  const setCell = (t, r, name, value) => {
    setAnswers((prev) => {
      const next = prev.map((a) => ({ ...a, rows: a.rows.map((row) => ({ ...row, vars: { ...row.vars } })) }));
      next[t].rows[r].vars[name] = value;
      return next;
    });
  };

  const setNextLine = (t, r, value) => {
    setAnswers((prev) => {
      const next = prev.map((a) => ({ ...a, rows: a.rows.map((row) => ({ ...row, vars: { ...row.vars } })) }));
      next[t].rows[r].next_line = value;
      return next;
    });
  };

  const setFinal = (t, value) => {
    setAnswers((prev) => {
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
        const answer = answers[t].rows[r];
        const emptyVar = Object.keys(table.rows[r].vars).find((n) => !answer.vars[n].trim());
        if (emptyVar) return `${table.call}, step ${table.rows[r].step}: value of ${emptyVar}`;
        if (!answer.next_line) return `${table.call}, step ${table.rows[r].step}: next line`;
      }
      if (!answers[t].final_output.trim()) return `${table.call}: return value`;
    }
    return null;
  };

  const handleSubmit = async () => {
    const missing = firstEmpty();
    if (missing) {
      setError(`Please fill in every cell before submitting — missing ${missing}.`);
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const traces = tables.map((table, t) => ({
        call: table.call,
        rows: table.rows.map((row, r) => ({
          step: row.step,
          vars: answers[t].rows[r].vars,
          next_line: answers[t].rows[r].next_line,
        })),
        final_output: answers[t].final_output,
      }));
      await api.submitTraces(session.session_id, traces);
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
        Here is the buggy implementation. For each sample input below, trace the
        code by hand and fill in the table: for every line that runs, give the
        value of each variable <em>after</em> that line has finished, and which
        line runs next. The first row is filled in for you as an example.
      </p>
      <p className="notice">
        You get <strong>one attempt</strong>, and you will not be told whether
        your answers were right — just do your best and move on.
      </p>
      <pre className="code-block">{buggyCode}</pre>

      {tables.map((table, t) => (
        <div key={table.call} className="trace-block">
          <h3>Trace: <code>{table.call}</code></h3>
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
                      <th>Line executed</th>
                      {table.var_names.map((name) => (
                        <th key={name}><code>{name}</code></th>
                      ))}
                      <th>Next line</th>
                    </tr>
                  </thead>
                  <tbody>
                    {table.rows.map((row, r) => (
                      <tr key={row.step} className={row.prefilled ? "prefilled" : ""}>
                        <td>{row.step}</td>
                        <td>
                          <code>
                            {row.lineno}: {row.line_text}
                          </code>
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
                                value={answers[t].rows[r].vars[name]}
                                onChange={(e) => setCell(t, r, name, e.target.value)}
                              />
                            )}
                          </td>
                        ))}
                        <td>
                          {row.prefilled ? (
                            <code>{row.next_line}</code>
                          ) : (
                            <select
                              aria-label={`${table.call} step ${row.step} next line`}
                              value={answers[t].rows[r].next_line}
                              onChange={(e) => setNextLine(t, r, e.target.value)}
                            >
                              <option value="">choose…</option>
                              {row.next_line_options.map((opt) => (
                                <option key={opt} value={opt}>{opt}</option>
                              ))}
                            </select>
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

      {error && <div className="error-banner">{error}</div>}

      <button onClick={handleSubmit} disabled={loading}>
        {loading ? "Submitting..." : "Submit trace"}
      </button>
    </div>
  );
}
