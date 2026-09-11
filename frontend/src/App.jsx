import React, { useState } from "react";
import TaskIntro from "./components/TaskIntro";
import Step1IOPairs from "./components/Step1IOPairs";
import Step2Trace from "./components/Step2Trace";
import Step3CounterExample from "./components/Step3CounterExample";

const STAGES = {
  INTRO: "intro",
  IO_PAIRS: "io_pairs",
  TRACE: "trace",
  COUNTER_EXAMPLE: "counter_example",
};

export default function App() {
  const [stage, setStage] = useState(STAGES.INTRO);
  const [session, setSession] = useState(null);
  const [buggyCode, setBuggyCode] = useState(null);
  const [traceTables, setTraceTables] = useState(null);
  const [dataFlowTables, setDataFlowTables] = useState(null);

  const stageOrder = [STAGES.IO_PAIRS, STAGES.TRACE, STAGES.COUNTER_EXAMPLE];
  const stageLabel = {
    [STAGES.IO_PAIRS]: "1. I/O Pairs",
    [STAGES.TRACE]: "2. Trace",
    [STAGES.COUNTER_EXAMPLE]: "3. Counter-example",
  };

  return (
    // The trace table needs more horizontal room than the rest of the flow.
    <div className={"app-shell" + (stage === STAGES.TRACE ? " wide" : "")}>
      {stage !== STAGES.INTRO && (
        <div className="step-indicator">
          {stageOrder.map((s) => (
            <div
              key={s}
              className={
                "step-dot " +
                (s === stage ? "active" : stageOrder.indexOf(s) < stageOrder.indexOf(stage) ? "done" : "")
              }
            >
              {stageLabel[s]}
            </div>
          ))}
        </div>
      )}

      {stage === STAGES.INTRO && (
        <TaskIntro
          onStarted={(sess) => {
            setSession(sess);
            setStage(STAGES.IO_PAIRS);
          }}
        />
      )}

      {stage === STAGES.IO_PAIRS && session && (
        <Step1IOPairs
          session={session}
          onCompleted={(code, tables, dataFlowTables) => {
            setBuggyCode(code);
            setTraceTables(tables);
            setDataFlowTables(dataFlowTables);
            setStage(STAGES.TRACE);
          }}
        />
      )}

      {stage === STAGES.TRACE && session && (
        <Step2Trace
          session={session}
          buggyCode={buggyCode}
          traceTables={traceTables}
          dataFlowTables={dataFlowTables}
          onCompleted={() => setStage(STAGES.COUNTER_EXAMPLE)}
        />
      )}

      {stage === STAGES.COUNTER_EXAMPLE && session && (
        <Step3CounterExample session={session} buggyCode={buggyCode} />
      )}
    </div>
  );
}
