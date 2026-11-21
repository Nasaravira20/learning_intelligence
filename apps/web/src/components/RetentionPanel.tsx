"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  LearningSession,
  RevisionReview,
  UiError,
  listReviews,
  startReview,
  submitReview,
  toUiError,
} from "@/lib/api";

export function RetentionPanel({
  sessions,
  refreshKey,
  onSession,
}: {
  sessions: LearningSession[];
  refreshKey: number;
  onSession: (session: LearningSession) => void;
}) {
  const [reviews, setReviews] = useState<RevisionReview[]>([]);
  const [answer, setAnswer] = useState("");
  const [reasoning, setReasoning] = useState("");
  const [error, setError] = useState<UiError | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    let active = true;
    listReviews()
      .then((next) => {
        if (active) {
          setReviews(next);
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
  }, [refreshKey, sessions]);

  function apply(next: RevisionReview) {
    const session = sessions.find((item) => item.id === next.session_id);
    if (session) {
      onSession({ ...session, status: next.session_status });
    }
    setReviews((current) => {
      const rest = current.filter((item) => item.id !== next.id);
      return [...rest, next];
    });
  }

  async function onStart(sessionId: string) {
    setError(null);
    setPending(true);
    try {
      apply(await startReview(sessionId));
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>, sessionId: string) {
    event.preventDefault();
    setError(null);
    setPending(true);
    try {
      apply(await submitReview(sessionId, answer, reasoning));
      setAnswer("");
      setReasoning("");
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(false);
    }
  }

  if (reviews.length === 0 && error === null) {
    return null;
  }

  return (
    <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
      <h2 className="text-lg font-semibold">Upcoming reviews</h2>
      {error ? (
        <div role="alert" className="mt-3 rounded-md border border-rose-300 bg-rose-50 px-3 py-2 text-sm text-rose-900">
          <p>{error.message}</p>
          <p className="mt-1 text-rose-800">Code: {error.code}</p>
        </div>
      ) : null}
      <ul className="mt-3 grid gap-3">
        {reviews.map((review) => (
          <li key={review.id} className="rounded border border-stone-200 p-3 text-sm">
            <p className="font-medium">
              {review.objective_code} · {review.timing} · due {review.due_on}
            </p>
            <p className="text-stone-700">
              Interval {review.interval_index + 1}. Timezone {review.timezone}.
              {review.was_missed ? " This date was missed." : ""}
            </p>
            {review.prompt ? <p className="mt-2">{review.prompt}</p> : null}
            {review.rubric.length > 0 ? (
              <ul className="mt-2 list-disc pl-5 text-stone-700">
                {review.rubric.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
            {review.status === "in_progress" ? (
              <form onSubmit={(event) => onSubmit(event, review.session_id)} className="mt-2 grid gap-2">
                <label className="grid gap-1" htmlFor={`review-answer-${review.id}`}>
                  Answer
                  <textarea
                    id={`review-answer-${review.id}`}
                    value={answer}
                    onChange={(event) => setAnswer(event.target.value)}
                    required
                    rows={3}
                    className="rounded border border-stone-300 px-2 py-1"
                  />
                </label>
                <label className="grid gap-1" htmlFor={`review-reason-${review.id}`}>
                  Reasoning
                  <textarea
                    id={`review-reason-${review.id}`}
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
                  className="w-fit rounded bg-stone-900 px-3 py-2 text-white disabled:opacity-50"
                >
                  Submit review
                </button>
              </form>
            ) : null}
            {review.outcome ? <p className="mt-2">Outcome {review.outcome}.</p> : null}
            {review.timing === "due" || review.timing === "missed" ? (
              <button
                type="button"
                onClick={() => onStart(review.session_id)}
                disabled={pending}
                className="mt-2 rounded bg-stone-900 px-3 py-2 text-white disabled:opacity-50"
              >
                Start review
              </button>
            ) : null}
          </li>
        ))}
      </ul>
    </section>
  );
}
