"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  EvaluationAttempt,
  LearningSession,
  UiError,
  getEvaluation,
  startEvaluation,
  startRemediation,
  submitEvaluation,
  toUiError,
} from "@/lib/api";

export function EvaluationPanel({
  session,
  refreshKey,
  onSession,
}: {
  session: LearningSession;
  refreshKey: number;
  onSession: (session: LearningSession) => void;
}) {
  const [evaluation, setEvaluation] = useState<EvaluationAttempt | null>(null);
  const [answer, setAnswer] = useState("");
  const [reasoning, setReasoning] = useState("");
  const [error, setError] = useState<UiError | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!["EVALUATING", "REMEDIATION", "MASTERED", "NEEDS_REVIEW"].includes(session.status)) {
      setEvaluation(null);
      return;
    }
    let active = true;
    getEvaluation(session.id)
      .then((next) => {
        if (active) {
          setEvaluation(next);
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
  }, [session.id, session.status, refreshKey]);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      const next = await submitEvaluation(session.id, answer, reasoning);
      setEvaluation(next);
      setAnswer("");
      setReasoning("");
      onSession({ ...session, status: next.session_status });
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  async function onAgain() {
    setError(null);
    setPending(true);
    try {
      const next = await startEvaluation(session.id);
      setEvaluation(next);
      onSession({ ...session, status: next.session_status });
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  async function onRemediate() {
    setError(null);
    setPending(true);
    try {
      const next = await startRemediation(session.id);
      onSession({ ...session, status: next.session_status });
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  if (!["EVALUATING", "REMEDIATION", "MASTERED", "NEEDS_REVIEW"].includes(session.status) || evaluation === null) {
    return null;
  }

  return (
    <div className="grid gap-3 rounded border border-stone-200 p-3">
      <h3 className="text-sm font-semibold">Check</h3>
      {error ? (
        <div role="alert" className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          <p>{error.message}</p>
          <p className="mt-1 text-rose-800">Code: {error.code}</p>
        </div>
      ) : null}
      <p className="text-sm text-stone-700">Objective {evaluation.objective_code}. Revision {evaluation.revision}.</p>
      <p>{evaluation.prompt}</p>
      <ul className="list-disc pl-5 text-sm text-stone-700">
        {evaluation.rubric.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
      {evaluation.status === "open" ? (
        <form onSubmit={onSubmit} className="grid gap-2">
          <label className="grid gap-1 text-sm" htmlFor={`answer-${evaluation.id}`}>
            Answer
            <textarea
              id={`answer-${evaluation.id}`}
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              required
              rows={3}
              className="rounded border border-stone-300 px-2 py-1"
            />
          </label>
          <label className="grid gap-1 text-sm" htmlFor={`reason-${evaluation.id}`}>
            Reasoning
            <textarea
              id={`reason-${evaluation.id}`}
              value={reasoning}
              onChange={(event) => setReasoning(event.target.value)}
              required
              rows={3}
              className="rounded border border-stone-300 px-2 py-1"
            />
          </label>
          <button
            type="submit"
            disabled={pending}
            className="w-fit rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50"
          >
            Submit check
          </button>
        </form>
      ) : (
        <div className="grid gap-2 text-sm">
          <p>
            Decision {evaluation.decision}. Credit {evaluation.credit}.
          </p>
          <p>{evaluation.feedback}</p>
          {evaluation.misconception_evidence ? (
            <p className="text-stone-700">Evidence from the answer: {evaluation.misconception_evidence}</p>
          ) : null}
          {evaluation.decision === "mastered" ? (
            <p className="text-stone-700">Observed evidence is recorded. A later review is on the schedule.</p>
          ) : null}
          {evaluation.decision === "needs_review" ? (
            <p className="text-stone-700">This result is not mastery.</p>
          ) : null}
          {evaluation.decision === "remediation" && evaluation.remediation_strategy ? (
            <p className="text-stone-700">Next strategy: {evaluation.remediation_strategy}.</p>
          ) : null}
          {evaluation.decision === "further_assessment" || evaluation.decision === "needs_review" ? (
            <button
              type="button"
              onClick={onAgain}
              disabled={pending}
              className="w-fit rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              Try another check
            </button>
          ) : null}
          {evaluation.decision === "remediation" && session.status === "REMEDIATION" ? (
            <button
              type="button"
              onClick={onRemediate}
              disabled={pending}
              className="w-fit rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              Teach a different way
            </button>
          ) : null}
        </div>
      )}
    </div>
  );
}
