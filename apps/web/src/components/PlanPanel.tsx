"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  DiagnosisReport,
  LearningPlan,
  LearningSession,
  PedagogySelection,
  UiError,
  chooseStrategies,
  createLearningPlan,
  getDiagnosis,
  getLearningPlan,
  getStrategySelection,
  reviseLearningPlan,
  startFollowUp,
  toUiError,
} from "@/lib/api";

function stepLabel(status: LearningPlan["steps"][number]["status"]): string {
  if (status === "current") {
    return "Start here";
  }
  if (status === "satisfied") {
    return "Already demonstrated";
  }
  return "Later";
}

export function PlanPanel({
  session,
  refreshKey,
  onSession,
  onRefresh,
}: {
  session: LearningSession;
  refreshKey: number;
  onSession: (session: LearningSession) => void;
  onRefresh: () => void;
}) {
  const [plan, setPlan] = useState<LearningPlan | null>(null);
  const [selection, setSelection] = useState<PedagogySelection | null>(null);
  const [diagnosisComplete, setDiagnosisComplete] = useState(false);
  const [followUpOpen, setFollowUpOpen] = useState(false);
  const [error, setError] = useState<UiError | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (session.status !== "DIAGNOSING" && session.status !== "PLAN_READY") {
      return;
    }
    let active = true;
    getDiagnosis(session.id)
      .then((report) => {
        if (!active) {
          return;
        }
        setDiagnosisComplete(report.status === "completed");
        setFollowUpOpen(report.status === "in_progress" && session.status === "PLAN_READY");
      })
      .catch(() => {
        if (active) {
          setDiagnosisComplete(false);
          setFollowUpOpen(false);
        }
      });
    if (session.status === "PLAN_READY") {
      getLearningPlan(session.id)
        .then((next) => {
          if (active) {
            setPlan(next);
          }
        })
        .catch((caught) => {
          if (!active) {
            return;
          }
          const uiError = toUiError(caught);
          if (uiError.code === "plan_not_found") {
            setPlan(null);
            return;
          }
          setError(uiError);
        });
      getStrategySelection(session.id)
        .then((next) => {
          if (active) {
            setSelection(next);
          }
        })
        .catch((caught) => {
          if (!active) {
            return;
          }
          const uiError = toUiError(caught);
          if (uiError.code === "selection_not_found") {
            setSelection(null);
            return;
          }
          setError(uiError);
        });
    }
    return () => {
      active = false;
    };
  }, [session.id, session.status, refreshKey]);

  async function onBuild() {
    setError(null);
    setPending(true);
    try {
      const next = await createLearningPlan(session.id);
      setPlan(next);
      setDiagnosisComplete(true);
      onSession({ ...session, status: next.session_status });
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  async function onRevise() {
    setError(null);
    setPending(true);
    try {
      setPlan(await reviseLearningPlan(session.id));
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  async function onChoose() {
    setError(null);
    setPending(true);
    try {
      setSelection(await chooseStrategies(session.id));
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  async function onFollowUp() {
    setError(null);
    setPending(true);
    try {
      await startFollowUp(session.id);
      setFollowUpOpen(true);
      onRefresh();
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  if (session.status !== "DIAGNOSING" && session.status !== "PLAN_READY") {
    return null;
  }
  if (!diagnosisComplete && plan === null) {
    return null;
  }

  return (
    <div className="grid gap-3 rounded border border-stone-200 p-3">
      <h3 className="text-sm font-semibold">Learning plan</h3>
      {error ? (
        <div role="alert" className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          <p>{error.message}</p>
          <p className="mt-1 text-rose-800">Code: {error.code}</p>
        </div>
      ) : null}
      {plan === null && diagnosisComplete ? (
        <button
          type="button"
          onClick={onBuild}
          disabled={pending}
          className="w-fit rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          Build learning plan
        </button>
      ) : null}
      {plan ? (
        <div className="grid gap-3 text-sm" aria-live="polite">
          <p>
            Revision {plan.revision}. {plan.summary}
          </p>
          <ol className="grid gap-3">
            {plan.steps.map((step) => (
              <li key={step.id} className="rounded border border-stone-200 px-3 py-2">
                <p className="font-medium">
                  {step.position + 1}. {stepLabel(step.status)} · {step.objective_code}
                </p>
                <p className="text-stone-700">
                  {step.concept}: {step.objective_statement}
                </p>
                <p className="text-stone-700">{step.completion_criteria}</p>
                <p className="text-stone-600">
                  {step.evidence === "observed" ? "Observed evidence" : "No evidence to skip this concept"}
                </p>
              </li>
            ))}
          </ol>
          {followUpOpen ? (
            <p className="text-stone-600">Finish the new diagnosis, then revise the plan.</p>
          ) : (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={onFollowUp}
                disabled={pending}
                className="rounded border border-stone-400 px-3 py-2 disabled:opacity-50"
              >
                Add diagnostic evidence
              </button>
              <button
                type="button"
                onClick={onRevise}
                disabled={pending}
                className="rounded border border-stone-400 px-3 py-2 disabled:opacity-50"
              >
                Revise plan
              </button>
              <button
                type="button"
                onClick={onChoose}
                disabled={pending}
                className="rounded border border-stone-400 px-3 py-2 disabled:opacity-50"
              >
                Choose strategies
              </button>
            </div>
          )}
          {selection ? (
            <div className="rounded border border-stone-200 px-3 py-2">
              <p className="font-medium">
                Benchmark strategy: {selection.primary_strategy}. Teaching has not started.
              </p>
              <p className="text-stone-700">
                Also considered: {selection.supporting_strategies.join(", ") || "none"}. Fallback:{" "}
                {selection.fallback_strategy}.
              </p>
              <ol className="mt-2 grid gap-1 text-stone-700">
                {selection.sequence.map((step, index) => (
                  <li key={`${index}-${step}`}>{step}</li>
                ))}
              </ol>
              <p className="mt-2 text-stone-600">{selection.rationale}</p>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
