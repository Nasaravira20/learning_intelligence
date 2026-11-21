"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  DiagnosisReport,
  LearningObjectiveRecord,
  LearningSession,
  UiError,
  addObjectivePrerequisite,
  createLearningObjective,
  getDiagnosis,
  listLearningObjectives,
  startDiagnosis,
  submitDiagnosis,
  toUiError,
} from "@/lib/api";

export function DiagnosticPanel({
  session,
  refreshKey,
  onSession,
}: {
  session: LearningSession;
  refreshKey: number;
  onSession: (session: LearningSession) => void;
}) {
  const [report, setReport] = useState<DiagnosisReport | null>(null);
  const [objectives, setObjectives] = useState<LearningObjectiveRecord[]>([]);
  const [error, setError] = useState<UiError | null>(null);
  const [pending, setPending] = useState(false);
  const [code, setCode] = useState("");
  const [statement, setStatement] = useState("");
  const [concept, setConcept] = useState("");
  const [prerequisites, setPrerequisites] = useState("");
  const [links, setLinks] = useState<Record<string, string>>({});
  const [answers, setAnswers] = useState<Record<string, { answer: string; reasoning: string }>>({});

  useEffect(() => {
    if (session.status !== "TOPIC_SELECTED") {
      return;
    }
    let active = true;
    listLearningObjectives(session.topic_id)
      .then((rows) => {
        if (active) {
          setObjectives(rows);
        }
      })
      .catch((caught) => {
        if (active) {
          setError(toUiError(caught));
        }
      });
    return () => {
      active = false;
    };
  }, [session.topic_id, session.status, refreshKey]);

  useEffect(() => {
    if (session.status !== "DIAGNOSING" && session.status !== "PLAN_READY") {
      return;
    }
    let active = true;
    getDiagnosis(session.id)
      .then((next) => {
        if (active) {
          setReport(next);
        }
      })
      .catch((caught) => {
        if (active) {
          const uiError = toUiError(caught);
          if (uiError.code !== "diagnosis_not_found") {
            setError(uiError);
          }
        }
      });
    return () => {
      active = false;
    };
  }, [session.id, session.status, refreshKey]);

  function applyReport(next: DiagnosisReport) {
    setReport(next);
    onSession({ ...session, status: next.session_status });
  }

  async function onStart() {
    setError(null);
    setPending(true);
    try {
      applyReport(await startDiagnosis(session.id));
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  async function onObjective(event: FormEvent) {
    event.preventDefault();
    const nextCode = code.trim();
    const nextStatement = statement.trim();
    const nextConcept = concept.trim();
    if (!nextCode || !nextStatement || !nextConcept) {
      setError({
        code: "validation_error",
        message: "An objective needs a code, a statement, and a concept.",
        requestId: null,
      });
      return;
    }
    setError(null);
    setPending(true);
    try {
      await createLearningObjective(
        session.topic_id,
        nextCode,
        nextStatement,
        nextConcept,
        prerequisites
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      );
      setCode("");
      setStatement("");
      setConcept("");
      setPrerequisites("");
      setObjectives(await listLearningObjectives(session.topic_id));
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  async function onLink(event: FormEvent, objectiveId: string) {
    event.preventDefault();
    const prerequisiteCode = (links[objectiveId] ?? "").trim();
    if (!prerequisiteCode) {
      setError({ code: "validation_error", message: "Enter a prerequisite code.", requestId: null });
      return;
    }
    setError(null);
    setPending(true);
    try {
      await addObjectivePrerequisite(session.topic_id, objectiveId, prerequisiteCode);
      setLinks((current) => ({ ...current, [objectiveId]: "" }));
      setObjectives(await listLearningObjectives(session.topic_id));
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  async function onResponses(event: FormEvent) {
    event.preventDefault();
    if (!report) {
      return;
    }
    setError(null);
    setPending(true);
    try {
      applyReport(
        await submitDiagnosis(
          session.id,
          report.questions.map((question) => ({
            question_id: question.id,
            answer_text: answers[question.id]?.answer ?? "",
            reasoning_text: answers[question.id]?.reasoning ?? "",
          })),
        ),
      );
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="mt-3 grid gap-3">
      {error ? (
        <div role="alert" className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          <p>{error.message}</p>
          <p className="mt-1 text-rose-800">Code: {error.code}</p>
        </div>
      ) : null}
      {session.status === "TOPIC_SELECTED" ? (
        <div className="grid gap-3">
          {objectives.length > 0 ? (
            <ul className="grid gap-2 text-sm">
              {objectives.map((objective) => (
                <li key={objective.id} className="rounded border border-stone-200 px-3 py-2">
                  <p className="font-medium">
                    {objective.code} · {objective.concept}
                  </p>
                  <p>{objective.statement}</p>
                  <p className="text-stone-600">
                    Prerequisites: {objective.prerequisite_codes.length > 0 ? objective.prerequisite_codes.join(", ") : "none"}
                  </p>
                  <form onSubmit={(event) => onLink(event, objective.id)} className="mt-2 flex flex-wrap gap-2">
                    <label className="text-stone-700" htmlFor={`link-${objective.id}`}>
                      Prerequisite code
                      <input
                        id={`link-${objective.id}`}
                        value={links[objective.id] ?? ""}
                        onChange={(event) => setLinks((current) => ({ ...current, [objective.id]: event.target.value }))}
                        className="ml-2 rounded border border-stone-300 px-2 py-1 font-mono"
                      />
                    </label>
                    <button type="submit" disabled={pending} className="rounded border border-stone-400 px-2 py-1 disabled:opacity-50">
                      Add prerequisite
                    </button>
                  </form>
                </li>
              ))}
            </ul>
          ) : null}
          <button
            type="button"
            onClick={onStart}
            disabled={pending}
            className="w-fit rounded border border-stone-400 px-3 py-2 text-sm disabled:opacity-50"
          >
            Start diagnosis
          </button>
        </div>
      ) : null}
      {session.status === "TOPIC_SELECTED" ? (
        <form onSubmit={onObjective} className="grid gap-2 rounded border border-stone-200 p-3">
          <h3 className="text-sm font-semibold">Learning objective</h3>
          <label className="text-sm text-stone-700" htmlFor={`objective-code-${session.id}`}>
            Code
            <input
              id={`objective-code-${session.id}`}
              value={code}
              onChange={(event) => setCode(event.target.value)}
              maxLength={64}
              className="mt-1 w-full rounded border border-stone-300 px-3 py-2 font-mono text-sm"
            />
          </label>
          <label className="text-sm text-stone-700" htmlFor={`objective-concept-${session.id}`}>
            Concept
            <input
              id={`objective-concept-${session.id}`}
              value={concept}
              onChange={(event) => setConcept(event.target.value)}
              maxLength={120}
              className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
            />
          </label>
          <label className="text-sm text-stone-700" htmlFor={`objective-statement-${session.id}`}>
            Statement
            <textarea
              id={`objective-statement-${session.id}`}
              value={statement}
              onChange={(event) => setStatement(event.target.value)}
              maxLength={300}
              className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
            />
          </label>
          <label className="text-sm text-stone-700" htmlFor={`objective-prerequisites-${session.id}`}>
            Prerequisite codes
            <input
              id={`objective-prerequisites-${session.id}`}
              value={prerequisites}
              onChange={(event) => setPrerequisites(event.target.value)}
              placeholder="Comma-separated codes already on this topic"
              className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
            />
          </label>
          <button type="submit" disabled={pending} className="w-fit rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50">
            Save objective
          </button>
        </form>
      ) : null}
      {report && report.status === "in_progress" ? (
        <form onSubmit={onResponses} className="grid gap-3 rounded border border-stone-200 p-3">
          <h3 className="text-sm font-semibold">Diagnostic questions</h3>
          {report.questions.map((question) => (
            <fieldset key={question.id} className="grid gap-2">
              <legend className="text-sm font-medium">
                {question.objective_code} · {question.format.replace(/_/g, " ")}
              </legend>
              <p className="text-sm">{question.prompt}</p>
              {question.choices ? (
                <ul className="list-disc pl-5 text-sm text-stone-700">
                  {question.choices.map((choice) => (
                    <li key={choice}>{choice}</li>
                  ))}
                </ul>
              ) : null}
              <label className="text-sm text-stone-700" htmlFor={`answer-${question.id}`}>
                Answer
                <textarea
                  id={`answer-${question.id}`}
                  value={answers[question.id]?.answer ?? ""}
                  onChange={(event) =>
                    setAnswers((current) => ({
                      ...current,
                      [question.id]: { answer: event.target.value, reasoning: current[question.id]?.reasoning ?? "" },
                    }))
                  }
                  maxLength={1000}
                  className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
                />
              </label>
              <label className="text-sm text-stone-700" htmlFor={`reasoning-${question.id}`}>
                Reasoning
                <textarea
                  id={`reasoning-${question.id}`}
                  value={answers[question.id]?.reasoning ?? ""}
                  onChange={(event) =>
                    setAnswers((current) => ({
                      ...current,
                      [question.id]: { answer: current[question.id]?.answer ?? "", reasoning: event.target.value },
                    }))
                  }
                  maxLength={1000}
                  className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
                />
              </label>
            </fieldset>
          ))}
          <button type="submit" disabled={pending} className="w-fit rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50">
            Submit diagnosis
          </button>
        </form>
      ) : null}
      {report && report.status === "completed" ? (
        <div className="rounded border border-stone-200 p-3 text-sm" aria-live="polite">
          <h3 className="font-semibold">Diagnostic report</h3>
          <p className="mt-1">{report.summary}</p>
          <p className="text-stone-600">
            Starting point: {report.starting_point}
            {report.confidence !== null ? ` · confidence ${report.confidence.toFixed(2)}` : ""}
          </p>
          <ul className="mt-2 space-y-2">
            {report.judgments.map((item) => (
              <li key={item.question_id}>
                {item.objective_code}: answer {item.answer_verdict}, reasoning {item.reasoning_verdict}
                {item.confirmed ? " · confirmed" : " · not confirmed"}
                {item.needs_review ? " · needs review" : ""}
              </li>
            ))}
          </ul>
          {report.misconceptions.length > 0 ? (
            <ul className="mt-2 space-y-1">
              {report.misconceptions.map((item) => (
                <li key={item.id}>
                  {item.concept}: {item.description}
                  {item.evidence ? ` Evidence: ${item.evidence}` : ""}
                  {item.confirmed ? " · confirmed" : " · not confirmed"}
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
