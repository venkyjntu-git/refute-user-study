const BASE_URL = process.env.REACT_APP_API_BASE || "";

async function request(path, options = {}) {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Request failed: ${res.status}`);
  }
  return res.json();
}

export const api = {
  listTasks: () => request("/api/tasks"),

  startSession: (student_identifier, task_id) =>
    request("/api/session", {
      method: "POST",
      body: JSON.stringify({ student_identifier, task_id }),
    }),

  markShown: (session_id, step) =>
    request("/api/event", {
      method: "POST",
      body: JSON.stringify({ session_id, step }),
    }),

  submitIOPairs: (session_id, pairs) =>
    request("/api/step1/submit", {
      method: "POST",
      body: JSON.stringify({ session_id, pairs }),
    }),

  submitTraces: (session_id, traces) =>
    request("/api/step2/submit", {
      method: "POST",
      body: JSON.stringify({ session_id, traces }),
    }),

  submitCounterExample: (session_id, call) =>
    request("/api/step3/submit", {
      method: "POST",
      body: JSON.stringify({ session_id, call }),
    }),
};
