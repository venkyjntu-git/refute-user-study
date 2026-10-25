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

  listLanguages: () => request("/api/languages"),

  startSession: (student_identifier, institute, language, task_id = null,
                 participant_id = null, position = null) =>
    request("/api/session", {
      method: "POST",
      body: JSON.stringify({
        student_identifier, institute, language, task_id, participant_id, position,
      }),
    }),

  // Counterbalanced study: create or resume a participant (server assigns
  // their two problems) — see register_participant in backend/main.py.
  registerParticipant: (survey) =>
    request("/api/participant", {
      method: "POST",
      body: JSON.stringify(survey),
    }),

  logSpecView: (session_id, step, version) =>
    request("/api/spec_view", {
      method: "POST",
      body: JSON.stringify({ session_id, step, version }),
    }),

  // Buggy code + trace tables again, for a session resumed past Step 1.
  getStepMaterials: (session_id) =>
    request("/api/step2/materials", {
      method: "POST",
      body: JSON.stringify({ session_id }),
    }),

  submitRefutation: (session_id, call, required_output, predicted_buggy_output, how_found) =>
    request("/api/step3/refute", {
      method: "POST",
      body: JSON.stringify({
        session_id, call, required_output, predicted_buggy_output, how_found,
      }),
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

  revealExamples: (session_id) =>
    request("/api/step1/examples", {
      method: "POST",
      body: JSON.stringify({ session_id }),
    }),

  submitTraces: (session_id, traces, data_flow_traces = [], mutation_response = null) =>
    request("/api/step2/submit", {
      method: "POST",
      body: JSON.stringify({ session_id, traces, data_flow_traces, mutation_response }),
    }),

  getMyWork: (session_id) =>
    request("/api/step3/my_work", {
      method: "POST",
      body: JSON.stringify({ session_id }),
    }),

  submitCounterExample: (session_id, call, predicted_correct_output, predicted_buggy_output) =>
    request("/api/step3/submit", {
      method: "POST",
      body: JSON.stringify({
        session_id, call, predicted_correct_output, predicted_buggy_output,
      }),
    }),
};
