"use client";

import { FormEvent, useEffect, useState } from "react";

import { LearningSession, TeachingLesson, UiError, getLesson, revealHint, submitTeachingAttempt, toUiError } from "@/lib/api";

const KIND_LABEL: Record<string, string> = {
  explanation: "Explanation",
  concrete_example: "Concrete example",
  worked_example: "Worked example",
  guided_practice: "Guided practice",
  independent_practice: "Independent practice",
  check_for_understanding: "Check for understanding",
  self_explanation: "Self-explanation",
};

export function TeachingPanel({
  session,
  refreshKey,
}: {
  session: LearningSession;
  refreshKey: number;
}) {
  const [lesson, setLesson] = useState<TeachingLesson | null>(null);
  const [answer, setAnswer] = useState("");
  const [error, setError] = useState<UiError | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (session.status !== "TEACHING") {
      setLesson(null);
      return;
    }
    let active = true;
    getLesson(session.id)
      .then((next) => {
        if (active) {
          setLesson(next);
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

  async function onHint() {
    setError(null);
    setPending(true);
    try {
      setLesson(await revealHint(session.id));
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  async function onAttempt(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const outcome = (event.nativeEvent as SubmitEvent).submitter?.getAttribute("value");
    if (outcome !== "correct" && outcome !== "struggled") {
      return;
    }
    setError(null);
    setPending(true);
    try {
      setLesson(await submitTeachingAttempt(session.id, outcome, answer));
      setAnswer("");
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  if (session.status !== "TEACHING" || lesson === null) {
    return null;
  }
  const current = lesson.activities.find((item) => item.id === lesson.current_activity_id) ?? null;

  return (
    <div className="grid gap-3 rounded border border-stone-200 p-3">
      <h3 className="text-sm font-semibold">Lesson</h3>
      {error ? (
        <div role="alert" className="rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          <p>{error.message}</p>
          <p className="mt-1 text-rose-800">Code: {error.code}</p>
        </div>
      ) : null}
      <p className="text-sm text-stone-700">
        Objective {lesson.objective_code}. Factuality review is still pending. Evaluation has not started.
      </p>
      <ol className="grid gap-3 text-sm">
        {lesson.activities.map((activity) => (
          <li key={activity.id} className="rounded border border-stone-200 px-3 py-2">
            <p className="font-medium">
              {activity.position + 1}. {KIND_LABEL[activity.kind] ?? activity.kind}
              {activity.status === "current" ? " · Current" : ""}
              {activity.inserted_for_struggle ? " · Added after a struggle" : ""}
            </p>
            <p className="text-stone-700">
              Strategy {activity.strategy_id}. Support {activity.support_level}.
            </p>
            <p>{activity.prompt}</p>
            {activity.example ? <p className="text-stone-700">Example: {activity.example}</p> : null}
            {activity.worked_steps.length > 0 ? (
              <ol className="list-decimal pl-5 text-stone-700">
                {activity.worked_steps.map((step) => (
                  <li key={step}>{step}</li>
                ))}
              </ol>
            ) : null}
            {activity.hints_revealed.length > 0 ? (
              <ul className="text-stone-700">
                {activity.hints_revealed.map((hint) => (
                  <li key={hint.position}>Hint {hint.position + 1}: {hint.text}</li>
                ))}
              </ul>
            ) : null}
          </li>
        ))}
      </ol>
      {lesson.status === "completed" ? (
        <p className="text-sm text-stone-600">Lesson activities are finished. Evaluation has not started.</p>
      ) : current ? (
        <form onSubmit={onAttempt} className="grid gap-2">
          <label className="grid gap-1 text-sm" htmlFor={`attempt-${current.id}`}>
            Your work on this step
            <textarea
              id={`attempt-${current.id}`}
              value={answer}
              onChange={(event) => setAnswer(event.target.value)}
              required
              rows={3}
              className="rounded border border-stone-300 px-2 py-1"
            />
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={onHint}
              disabled={pending || current.hints_revealed.length >= current.hints_available}
              className="rounded border border-stone-400 px-3 py-2 text-sm disabled:opacity-50"
            >
              Show a hint
            </button>
            <button
              type="submit"
              value="struggled"
              disabled={pending}
              className="rounded border border-stone-400 px-3 py-2 text-sm disabled:opacity-50"
            >
              I need more support
            </button>
            <button
              type="submit"
              value="correct"
              disabled={pending}
              className="rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50"
            >
              Continue
            </button>
          </div>
        </form>
      ) : null}
    </div>
  );
}
