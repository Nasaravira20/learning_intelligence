"use client";

import { FormEvent, useEffect, useState } from "react";

import {
  Account,
  Health,
  LearningSession,
  Topic,
  createSession,
  createTopic,
  currentAccount,
  getHealth,
  listSessions,
  listTopics,
  resumeSession,
  signOut,
  toUiError,
  UiError,
} from "@/lib/api";
import { slugify } from "@/lib/slug";
import { DiagnosticPanel } from "@/components/DiagnosticPanel";
import { PlanPanel } from "@/components/PlanPanel";
import { TeachingPanel } from "@/components/TeachingPanel";
import { LearnerDashboard } from "@/components/LearnerDashboard";

function ErrorBanner({ error }: { error: UiError }) {
  return (
    <div role="alert" className="rounded-md border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-900">
      <p>{error.message}</p>
      <p className="mt-1 text-rose-800">Code: {error.code}</p>
      {error.requestId ? <p className="mt-1 font-mono text-xs text-rose-800">Request ID: {error.requestId}</p> : null}
    </div>
  );
}

function sessionStatusLabel(status: string): string {
  if (status === "DIAGNOSING") {
    return "Diagnosing";
  }
  if (status === "PLAN_READY") {
    return "Plan ready";
  }
  if (status === "TEACHING") {
    return "Teaching";
  }
  if (status === "TOPIC_SELECTED") {
    return "Topic selected";
  }
  return status;
}

function formatWhen(value: string | null): string {
  if (!value) {
    return "Not resumed";
  }
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "Not resumed";
  }
  return parsed.toLocaleString();
}

export function TeacherShell() {
  const [account, setAccount] = useState<Account | null>(null);
  const [health, setHealth] = useState<Health | null>(null);
  const [healthError, setHealthError] = useState<UiError | null>(null);
  const [formError, setFormError] = useState<UiError | null>(null);
  const [topics, setTopics] = useState<Topic[]>([]);
  const [sessions, setSessions] = useState<LearningSession[]>([]);
  const [title, setTitle] = useState("");
  const [slug, setSlug] = useState("");
  const [slugTouched, setSlugTouched] = useState(false);
  const [description, setDescription] = useState("");
  const [topicId, setTopicId] = useState("");
  const [pending, setPending] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);

  function replaceSession(updated: LearningSession) {
    setSessions((current) => current.map((item) => (item.id === updated.id ? { ...item, ...updated } : item)));
    setRefreshKey((value) => value + 1);
  }

  async function refreshHealth() {
    try {
      const next = await getHealth();
      setHealth(next);
      setHealthError(null);
    } catch (error) {
      setHealth(null);
      setHealthError(toUiError(error));
    }
  }

  async function refreshLists() {
    const [topicResult, sessionResult] = await Promise.allSettled([listTopics(), listSessions()]);
    if (topicResult.status === "fulfilled") {
      setTopics(topicResult.value);
      setTopicId((current) => current || topicResult.value[0]?.id || "");
    }
    if (sessionResult.status === "fulfilled") {
      setSessions(sessionResult.value);
    }
    const firstFailure = [topicResult, sessionResult].find((result) => result.status === "rejected");
    if (firstFailure && firstFailure.status === "rejected") {
      setFormError(toUiError(firstFailure.reason));
    }
  }

  useEffect(() => {
    let active = true;
    currentAccount()
      .then((nextAccount) => {
        if (!active) {
          return;
        }
        setAccount(nextAccount);
        return Promise.all([refreshHealth(), refreshLists()]);
      })
      .catch((error) => {
        const uiError = toUiError(error);
        if (uiError.code === "unauthenticated") {
          window.location.assign("/signin");
          return;
        }
        if (active) {
          setFormError(uiError);
        }
      })
      .finally(() => {
        if (active) {
          setLoading(false);
        }
      });
    return () => {
      active = false;
    };
  }, []);

  async function onSignOut() {
    setPending("signout");
    try {
      await signOut();
      window.location.assign("/");
    } catch (error) {
      setFormError(toUiError(error));
      setPending(null);
    }
  }

  async function onCreateTopic(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    const nextTitle = title.trim();
    const nextSlug = slug.trim();
    if (!nextTitle || !nextSlug) {
      setFormError({
        code: "validation_error",
        message: "A topic needs a title and a lowercase slug.",
        requestId: null,
      });
      return;
    }
    setPending("topic");
    try {
      const topic = await createTopic(nextTitle, nextSlug, description);
      setTopics((current) => [...current, topic]);
      setTopicId(topic.id);
      setTitle("");
      setSlug("");
      setSlugTouched(false);
      setDescription("");
    } catch (error) {
      setFormError(toUiError(error));
    } finally {
      setPending(null);
    }
  }

  async function onCreateSession(event: FormEvent) {
    event.preventDefault();
    setFormError(null);
    if (!account || !topicId) {
      setFormError({
        code: "validation_error",
        message: "Choose a topic before starting a session.",
        requestId: null,
      });
      return;
    }
    setPending("session");
    try {
      const learningSession = await createSession(account.learner_id, topicId);
      setSessions((current) => [learningSession, ...current]);
    } catch (error) {
      setFormError(toUiError(error));
    } finally {
      setPending(null);
    }
  }

  async function onResume(sessionId: string) {
    setFormError(null);
    setPending(sessionId);
    try {
      const updated = await resumeSession(sessionId);
      setSessions((current) => current.map((item) => (item.id === updated.id ? updated : item)));
    } catch (error) {
      setFormError(toUiError(error));
    } finally {
      setPending(null);
    }
  }

  const apiReady = health?.status === "ok" && health.database === "ok";

  if (!account) {
    return (
      <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-4 py-8">
        {formError ? <ErrorBanner error={formError} /> : <p className="text-stone-600">Checking your account.</p>}
      </main>
    );
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-5xl flex-col gap-6 px-4 py-8">
      <header className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm uppercase tracking-wide text-stone-500">MNEMO · Teacher Mode</p>
          <h1 className="text-3xl font-semibold text-stone-900">{account.display_name}</h1>
        </div>
        <div className="flex items-center gap-3">
          <p
            className={`rounded-full px-3 py-1 text-sm ${apiReady ? "bg-emerald-100 text-emerald-900" : "bg-rose-100 text-rose-900"}`}
            role="status"
          >
            {apiReady ? "API ready" : "API unavailable"}
          </p>
          <button
            type="button"
            onClick={onSignOut}
            disabled={pending !== null}
            className="rounded border border-stone-400 px-3 py-2 text-sm disabled:opacity-50"
          >
            Sign out
          </button>
        </div>
      </header>

      {healthError ? <ErrorBanner error={healthError} /> : null}
      {formError ? <ErrorBanner error={formError} /> : null}
      {loading ? <p className="text-stone-600">Loading your sessions.</p> : null}

      <LearnerDashboard
        topics={topics}
        sessions={sessions}
        onDisplayName={(name) => setAccount((current) => (current ? { ...current, display_name: name } : current))}
      />

      <section className="grid gap-4">
        <form onSubmit={onCreateTopic} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
          <h2 className="text-lg font-semibold">Topic</h2>
          <label className="mt-3 block text-sm text-stone-700" htmlFor="topic-title">
            Topic title
          </label>
          <input
            id="topic-title"
            value={title}
            onChange={(event) => {
              const next = event.target.value;
              setTitle(next);
              if (!slugTouched) {
                setSlug(slugify(next));
              }
            }}
            maxLength={120}
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
          />
          <label className="mt-3 block text-sm text-stone-700" htmlFor="topic-slug">
            Slug
          </label>
          <input
            id="topic-slug"
            value={slug}
            onChange={(event) => {
              setSlugTouched(true);
              setSlug(event.target.value);
            }}
            maxLength={80}
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2 font-mono text-sm"
          />
          <label className="mt-3 block text-sm text-stone-700" htmlFor="topic-description">
            Description
          </label>
          <textarea
            id="topic-description"
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            maxLength={2000}
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
          />
          <button
            type="submit"
            disabled={pending !== null}
            className="mt-3 rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50"
          >
            Create topic
          </button>
        </form>
      </section>

      <form onSubmit={onCreateSession} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold">Start a session</h2>
        <p className="mt-1 text-sm text-stone-600">This session is saved to {account.display_name}.</p>
        <div className="mt-3 grid gap-3">
          <label className="text-sm text-stone-700" htmlFor="session-topic">
            Topic
            <select
              id="session-topic"
              value={topicId}
              onChange={(event) => setTopicId(event.target.value)}
              className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
            >
              <option value="">Choose a topic</option>
              {topics.map((topic) => (
                <option key={topic.id} value={topic.id}>
                  {topic.title}
                </option>
              ))}
            </select>
          </label>
        </div>
        <button
          type="submit"
          disabled={pending !== null || !topicId}
          className="mt-3 rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50"
        >
          Start session
        </button>
      </form>

      <section className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h2 className="text-lg font-semibold">Saved sessions</h2>
        {sessions.length === 0 ? <p className="mt-3 text-sm text-stone-600">No sessions yet.</p> : null}
        <ul className="mt-3 divide-y divide-stone-200">
          {sessions.map((session) => (
            <li key={session.id} className="grid gap-3 py-3">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <div>
                  <p className="font-medium">
                    {session.learner_name} · {session.topic_title}
                  </p>
                  <p className="text-sm text-stone-600">Status: {sessionStatusLabel(session.status)}</p>
                  <p className="text-sm text-stone-600">Resumed: {formatWhen(session.resumed_at)}</p>
                </div>
                <button
                  type="button"
                  onClick={() => onResume(session.id)}
                  disabled={pending !== null}
                  aria-label={`Resume ${session.topic_title}`}
                  className="rounded border border-stone-400 px-3 py-2 text-sm disabled:opacity-50"
                >
                  Resume
                </button>
              </div>
              <DiagnosticPanel session={session} refreshKey={refreshKey} onSession={replaceSession} />
              <PlanPanel
                session={session}
                refreshKey={refreshKey}
                onSession={replaceSession}
                onRefresh={() => setRefreshKey((value) => value + 1)}
              />
              <TeachingPanel session={session} refreshKey={refreshKey} />
            </li>
          ))}
        </ul>
      </section>
    </main>
  );
}
