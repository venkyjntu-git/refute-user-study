import React, { useState } from "react";
import { api } from "./api";
import TaskIntro from "./components/TaskIntro";
import Step1IOPairs from "./components/Step1IOPairs";
import Step2Trace from "./components/Step2Trace";
import Step3CounterExample from "./components/Step3CounterExample";

const STAGES = {
  INTRO: "intro",
  IO_PAIRS: "io_pairs",
  TRACE: "trace",
  COUNTER_EXAMPLE: "counter_example",
  ALL_DONE: "all_done",
};

export default function App() {
  const [stage, setStage] = useState(STAGES.INTRO);
  const [session, setSession] = useState(null);
  const [buggyCode, setBuggyCode] = useState(null);
  const [traceTables, setTraceTables] = useState(null);
  const [dataFlowTables, setDataFlowTables] = useState(null);
  const [mutation, setMutation] = useState(null);
  // The full ordered (by task id) list of tasks for the chosen language,
  // fetched once the first session starts, plus where the student
  // currently sits in it — drives "next problem" advancement in Step 3.
  const [taskList, setTaskList] = useState([]);
  const [taskIndex, setTaskIndex] = useState(0);
  const [nextTaskError, setNextTaskError] = useState(null);

  const resetTaskState = () => {
    setBuggyCode(null);
    setTraceTables(null);
    setDataFlowTables(null);
    setMutation(null);
  };

  const handleNextTask = async () => {
    const nextIndex = taskIndex + 1;
    if (!session || nextIndex >= taskList.length) {
      setStage(STAGES.ALL_DONE);
      return;
    }
    setNextTaskError(null);
    try {
      const nextSession = await api.startSession(
        session.student_identifier, session.institute, session.language,
        taskList[nextIndex].id,
      );
      resetTaskState();
      setSession(nextSession);
      setTaskIndex(nextIndex);
      setStage(STAGES.IO_PAIRS);
    } catch (e) {
      setNextTaskError(e.message);
    }
  };

  const stageOrder = [STAGES.IO_PAIRS, STAGES.TRACE, STAGES.COUNTER_EXAMPLE];
  const stageLabel = {
    [STAGES.IO_PAIRS]: "1. I/O Pairs",
    [STAGES.TRACE]: "2. Trace",
    [STAGES.COUNTER_EXAMPLE]: "3. Counter-example",
  };

  return (
    // The trace table needs more horizontal room than the rest of the flow.
    <div className={"app-shell" + (stage === STAGES.TRACE ? " wide" : "")}>
      {stage !== STAGES.INTRO && stage !== STAGES.ALL_DONE && (
        <div className="step-indicator">
          {taskList.length > 1 && (
            <div className="task-progress">Problem {taskIndex + 1} of {taskList.length}</div>
          )}
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
          onStarted={async (sess) => {
            setSession(sess);
            try {
              // The whole ordered (by id) task list for this language, so
              // "next problem" (Step 3) knows what comes after this one.
              // Fetched once, up front, rather than re-queried per
              // advancement — the list doesn't change mid-study.
              const allTasks = await api.listTasks();
              const languageTasks = allTasks
                .filter((t) => t.language === sess.language)
                .sort((a, b) => a.id - b.id);
              setTaskList(languageTasks);
              const idx = languageTasks.findIndex((t) => t.id === sess.task_id);
              setTaskIndex(idx >= 0 ? idx : 0);
            } catch {
              // Non-fatal: the study still works for this one task, it just
              // won't offer a "next problem" step afterward.
              setTaskList([]);
            }
            setStage(STAGES.IO_PAIRS);
          }}
        />
      )}

      {stage === STAGES.IO_PAIRS && session && (
        <Step1IOPairs
          session={session}
          onCompleted={(code, tables, dataFlowTables, mutationConfig) => {
            setBuggyCode(code);
            setTraceTables(tables);
            setDataFlowTables(dataFlowTables);
            setMutation(mutationConfig);
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
          mutation={mutation}
          onCompleted={() => setStage(STAGES.COUNTER_EXAMPLE)}
        />
      )}

      {stage === STAGES.COUNTER_EXAMPLE && session && (
        <Step3CounterExample
          session={session}
          buggyCode={buggyCode}
          onNext={handleNextTask}
          nextError={nextTaskError}
          hasNextTask={taskIndex + 1 < taskList.length}
        />
      )}

      {stage === STAGES.ALL_DONE && (
        <div className="card">
          <h2>All done!</h2>
          <p>
            You've completed all {taskList.length || ""} problems in this
            study. Thank you for your time and effort!
          </p>
        </div>
      )}
    </div>
  );
}
