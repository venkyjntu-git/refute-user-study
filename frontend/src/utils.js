// The function name is fixed decoration around a call-input box, not
// something the student types — a typo'd or missing function name would
// trip the "couldn't run" path for a reason that has nothing to do with
// what these steps actually measure, and Method.md's own design says that
// path should only ever say "check the name and arguments," never why.
// Locking the name removes that failure mode outright: the only thing left
// for the student to get wrong is the arguments, which is the actual test.
// Shared by Step1IOPairs (I/O pairs) and Step3CounterExample (the
// counter-example call) — both build a call as `${funcName}(${args})`.
export function extractFunctionName(signature) {
  const match = /^def\s+([A-Za-z_]\w*)/.exec(signature || "");
  return match ? match[1] : "";
}
