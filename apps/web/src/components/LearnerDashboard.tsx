"use client";

import { FormEvent, useEffect, useState } from "react";

import { evidenceLabel } from "@/lib/evidence";
import {
  KnowledgeRecord,
  LearnerDashboardData,
  LearningSession,
  SessionHistory,
  Topic,
  UiError,
  correctKnowledge,
  createLearningGoal,
  getLearnerDashboard,
  getSessionHistory,
  recordAssessment,
  recordKnowledge,
  saveLearnerPreferences,
  toUiError,
  updateLearnerProfile,
} from "@/lib/api";

function Banner({ error }: { error: UiError }) {
  return (
    <div role="alert" className="rounded-md border border-rose-300 bg-rose-50 px-4 py-3 text-sm text-rose-900">
      <p>{error.message}</p>
      <p className="mt-1 text-rose-800">Code: {error.code}</p>
    </div>
  );
}

export function LearnerDashboard({
  topics,
  sessions,
  onDisplayName,
}: {
  topics: Topic[];
  sessions: LearningSession[];
  onDisplayName: (name: string) => void;
}) {
  const [data, setData] = useState<LearnerDashboardData | null>(null);
  const [error, setError] = useState<UiError | null>(null);
  const [pending, setPending] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [backgroundNote, setBackgroundNote] = useState("");
  const [pace, setPace] = useState<"unhurried" | "steady" | "intensive">("steady");
  const [detail, setDetail] = useState<"concise" | "balanced" | "thorough">("balanced");
  const [practiceFirst, setPracticeFirst] = useState(false);
  const [preferenceNotes, setPreferenceNotes] = useState("");
  const [goal, setGoal] = useState("");
  const [goalTopicId, setGoalTopicId] = useState("");
  const [concept, setConcept] = useState("");
  const [summary, setSummary] = useState("");
  const [knowledgeTopicId, setKnowledgeTopicId] = useState("");
  const [correctionId, setCorrectionId] = useState("");
  const [correctionSummary, setCorrectionSummary] = useState("");
  const [correctionNote, setCorrectionNote] = useState("");
  const [promptSummary, setPromptSummary] = useState("");
  const [responseSummary, setResponseSummary] = useState("");
  const [assessmentTopicId, setAssessmentTopicId] = useState("");
  const [history, setHistory] = useState<SessionHistory | null>(null);

  async function refresh() {
    const next = await getLearnerDashboard();
    setData(next);
    setDisplayName(next.profile.display_name);
    setBackgroundNote(next.profile.background_note ?? "");
    if (next.preferences) {
      setPace(next.preferences.pace);
      setDetail(next.preferences.explanation_detail);
      setPracticeFirst(next.preferences.practice_first);
      setPreferenceNotes(next.preferences.notes ?? "");
    }
    setKnowledgeTopicId((current) => current || topics[0]?.id || "");
    setGoalTopicId((current) => current || topics[0]?.id || "");
    setAssessmentTopicId((current) => current || topics[0]?.id || "");
    setCorrectionId((current) =>
      next.knowledge.some((item) => item.id === current) ? current : next.knowledge[0]?.id || "",
    );
  }

  useEffect(() => {
    let active = true;
    getLearnerDashboard()
      .then((next) => {
        if (!active) {
          return;
        }
        setData(next);
        setDisplayName(next.profile.display_name);
        setBackgroundNote(next.profile.background_note ?? "");
        if (next.preferences) {
          setPace(next.preferences.pace);
          setDetail(next.preferences.explanation_detail);
          setPracticeFirst(next.preferences.practice_first);
          setPreferenceNotes(next.preferences.notes ?? "");
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
  }, []);

  useEffect(() => {
    setKnowledgeTopicId((current) => current || topics[0]?.id || "");
    setGoalTopicId((current) => current || topics[0]?.id || "");
    setAssessmentTopicId((current) => current || topics[0]?.id || "");
  }, [topics]);

  async function run(name: string, action: () => Promise<void>) {
    setError(null);
    setPending(name);
    try {
      await action();
      await refresh();
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(null);
    }
  }

  async function onProfile(event: FormEvent) {
    event.preventDefault();
    const nextName = displayName.trim();
    if (!nextName) {
      setError({ code: "validation_error", message: "Display name is required.", requestId: null });
      return;
    }
    await run("profile", async () => {
      const profile = await updateLearnerProfile(nextName, backgroundNote);
      onDisplayName(profile.display_name);
    });
  }

  async function onPreferences(event: FormEvent) {
    event.preventDefault();
    await run("preferences", async () => {
      await saveLearnerPreferences(pace, detail, practiceFirst, preferenceNotes);
    });
  }

  async function onGoal(event: FormEvent) {
    event.preventDefault();
    if (!goal.trim()) {
      setError({ code: "validation_error", message: "A learning goal needs a statement.", requestId: null });
      return;
    }
    await run("goal", async () => {
      await createLearningGoal(goal.trim(), goalTopicId);
      setGoal("");
    });
  }

  async function onKnowledge(event: FormEvent) {
    event.preventDefault();
    if (!knowledgeTopicId || !concept.trim() || !summary.trim()) {
      setError({ code: "validation_error", message: "Knowledge needs a topic, concept, and summary.", requestId: null });
      return;
    }
    await run("knowledge", async () => {
      await recordKnowledge(knowledgeTopicId, concept.trim(), summary.trim(), 0.4);
      setConcept("");
      setSummary("");
    });
  }

  async function onCorrect(event: FormEvent) {
    event.preventDefault();
    if (!correctionId || !correctionSummary.trim() || !correctionNote.trim()) {
      setError({
        code: "validation_error",
        message: "A correction needs the record, a new summary, and a note.",
        requestId: null,
      });
      return;
    }
    await run("correct", async () => {
      await correctKnowledge(correctionId, correctionSummary.trim(), correctionNote.trim());
      setCorrectionSummary("");
      setCorrectionNote("");
    });
  }

  async function onAssessment(event: FormEvent) {
    event.preventDefault();
    if (!assessmentTopicId || !promptSummary.trim() || !responseSummary.trim()) {
      setError({
        code: "validation_error",
        message: "An assessment note needs a topic, what was asked, and what you answered.",
        requestId: null,
      });
      return;
    }
    await run("assessment", async () => {
      await recordAssessment(assessmentTopicId, promptSummary.trim(), responseSummary.trim());
      setPromptSummary("");
      setResponseSummary("");
    });
  }

  async function onHistory(sessionId: string) {
    setError(null);
    setPending(sessionId);
    try {
      setHistory(await getSessionHistory(sessionId));
    } catch (caught) {
      setError(toUiError(caught));
    } finally {
      setPending(null);
    }
  }

  const knowledge = data?.knowledge ?? [];

  return (
    <section className="grid gap-4" aria-label="Learner record">
      <div>
        <h2 className="text-lg font-semibold">Learner record</h2>
        <p className="mt-1 text-sm text-stone-600">
          Observed means you demonstrated it. Inferred means it is an estimate or a self-report, not confirmed knowledge.
        </p>
      </div>
      {error ? <Banner error={error} /> : null}

      <form onSubmit={onProfile} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold">Profile</h3>
        <label className="mt-3 block text-sm text-stone-700" htmlFor="profile-name">
          Display name
        </label>
        <input
          id="profile-name"
          value={displayName}
          onChange={(event) => setDisplayName(event.target.value)}
          maxLength={80}
          className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
        />
        <label className="mt-3 block text-sm text-stone-700" htmlFor="profile-background">
          Background note
        </label>
        <textarea
          id="profile-background"
          value={backgroundNote}
          onChange={(event) => setBackgroundNote(event.target.value)}
          maxLength={500}
          className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
        />
        <button type="submit" disabled={pending !== null} className="mt-3 rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50">
          Save profile
        </button>
      </form>

      <form onSubmit={onPreferences} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold">Preferences</h3>
        <label className="mt-3 block text-sm text-stone-700" htmlFor="preference-pace">
          Pace
          <select
            id="preference-pace"
            value={pace}
            onChange={(event) => setPace(event.target.value as typeof pace)}
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
          >
            <option value="unhurried">Unhurried</option>
            <option value="steady">Steady</option>
            <option value="intensive">Intensive</option>
          </select>
        </label>
        <label className="mt-3 block text-sm text-stone-700" htmlFor="preference-detail">
          Explanation detail
          <select
            id="preference-detail"
            value={detail}
            onChange={(event) => setDetail(event.target.value as typeof detail)}
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
          >
            <option value="concise">Concise</option>
            <option value="balanced">Balanced</option>
            <option value="thorough">Thorough</option>
          </select>
        </label>
        <label className="mt-3 flex items-center gap-2 text-sm text-stone-700" htmlFor="preference-practice">
          <input
            id="preference-practice"
            type="checkbox"
            checked={practiceFirst}
            onChange={(event) => setPracticeFirst(event.target.checked)}
          />
          Practice before the longer explanation
        </label>
        <label className="mt-3 block text-sm text-stone-700" htmlFor="preference-notes">
          Preference note
          <textarea
            id="preference-notes"
            value={preferenceNotes}
            onChange={(event) => setPreferenceNotes(event.target.value)}
            maxLength={500}
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
          />
        </label>
        <button type="submit" disabled={pending !== null} className="mt-3 rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50">
          Save preferences
        </button>
      </form>

      <form onSubmit={onGoal} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold">Learning goals</h3>
        <label className="mt-3 block text-sm text-stone-700" htmlFor="goal-statement">
          Goal
        </label>
        <input
          id="goal-statement"
          value={goal}
          onChange={(event) => setGoal(event.target.value)}
          maxLength={300}
          className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
        />
        <label className="mt-3 block text-sm text-stone-700" htmlFor="goal-topic">
          Topic
          <select
            id="goal-topic"
            value={goalTopicId}
            onChange={(event) => setGoalTopicId(event.target.value)}
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
          >
            <option value="">No specific topic</option>
            {topics.map((topic) => (
              <option key={topic.id} value={topic.id}>
                {topic.title}
              </option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={pending !== null} className="mt-3 rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50">
          Add goal
        </button>
        <ul className="mt-3 space-y-2 text-sm">
          {(data?.goals ?? []).length === 0 ? <li className="text-stone-600">No goals yet.</li> : null}
          {(data?.goals ?? []).map((item) => (
            <li key={item.id}>
              {item.statement} <span className="text-stone-500">({item.status})</span>
            </li>
          ))}
        </ul>
      </form>

      <form onSubmit={onKnowledge} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold">Topic knowledge</h3>
        <p className="mt-1 text-sm text-stone-600">A self-report is stored as inferred. It is not treated as demonstrated knowledge.</p>
        <label className="mt-3 block text-sm text-stone-700" htmlFor="knowledge-topic">
          Topic
          <select
            id="knowledge-topic"
            value={knowledgeTopicId}
            onChange={(event) => setKnowledgeTopicId(event.target.value)}
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
        <label className="mt-3 block text-sm text-stone-700" htmlFor="knowledge-concept">
          Concept
        </label>
        <input
          id="knowledge-concept"
          value={concept}
          onChange={(event) => setConcept(event.target.value)}
          maxLength={120}
          className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
        />
        <label className="mt-3 block text-sm text-stone-700" htmlFor="knowledge-summary">
          Summary
        </label>
        <textarea
          id="knowledge-summary"
          value={summary}
          onChange={(event) => setSummary(event.target.value)}
          maxLength={1000}
          className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
        />
        <button type="submit" disabled={pending !== null} className="mt-3 rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50">
          Record knowledge
        </button>
        <ul className="mt-4 space-y-3">
          {knowledge.length === 0 ? <li className="text-sm text-stone-600">No knowledge recorded yet.</li> : null}
          {knowledge.map((item) => (
            <KnowledgeItem key={item.id} item={item} topicTitle={topics.find((topic) => topic.id === item.topic_id)?.title} />
          ))}
        </ul>
      </form>

      <form onSubmit={onCorrect} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold">Correct a knowledge record</h3>
        <p className="mt-1 text-sm text-stone-600">The correction updates the summary and keeps the original evidence kind.</p>
        <label className="mt-3 block text-sm text-stone-700" htmlFor="correction-record">
          Record
          <select
            id="correction-record"
            value={correctionId}
            onChange={(event) => setCorrectionId(event.target.value)}
            className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
          >
            <option value="">Choose a record</option>
            {knowledge.map((item) => (
              <option key={item.id} value={item.id}>
                {item.concept}
              </option>
            ))}
          </select>
        </label>
        <label className="mt-3 block text-sm text-stone-700" htmlFor="correction-summary">
          Corrected summary
        </label>
        <textarea
          id="correction-summary"
          value={correctionSummary}
          onChange={(event) => setCorrectionSummary(event.target.value)}
          maxLength={1000}
          className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
        />
        <label className="mt-3 block text-sm text-stone-700" htmlFor="correction-note">
          Correction note
        </label>
        <input
          id="correction-note"
          value={correctionNote}
          onChange={(event) => setCorrectionNote(event.target.value)}
          maxLength={500}
          className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
        />
        <button type="submit" disabled={pending !== null} className="mt-3 rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50">
          Save correction
        </button>
      </form>

      <form onSubmit={onAssessment} className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold">Assessment history</h3>
        <label className="mt-3 block text-sm text-stone-700" htmlFor="assessment-topic">
          Topic
          <select
            id="assessment-topic"
            value={assessmentTopicId}
            onChange={(event) => setAssessmentTopicId(event.target.value)}
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
        <label className="mt-3 block text-sm text-stone-700" htmlFor="assessment-prompt">
          What was asked
        </label>
        <input
          id="assessment-prompt"
          value={promptSummary}
          onChange={(event) => setPromptSummary(event.target.value)}
          maxLength={500}
          className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
        />
        <label className="mt-3 block text-sm text-stone-700" htmlFor="assessment-response">
          What you answered
        </label>
        <textarea
          id="assessment-response"
          value={responseSummary}
          onChange={(event) => setResponseSummary(event.target.value)}
          maxLength={2000}
          className="mt-1 w-full rounded border border-stone-300 px-3 py-2"
        />
        <button type="submit" disabled={pending !== null} className="mt-3 rounded bg-stone-900 px-3 py-2 text-sm text-white disabled:opacity-50">
          Record assessment
        </button>
        <ul className="mt-3 space-y-2 text-sm">
          {(data?.assessments ?? []).length === 0 ? <li className="text-stone-600">No assessments yet.</li> : null}
          {(data?.assessments ?? []).map((item) => (
            <li key={item.id}>
              {item.prompt_summary} — {item.response_summary} <span className="text-stone-500">({item.outcome})</span>
            </li>
          ))}
        </ul>
      </form>

      <div className="rounded-lg border border-stone-200 bg-white p-4 shadow-sm">
        <h3 className="font-semibold">Session history</h3>
        {sessions.length === 0 ? <p className="mt-3 text-sm text-stone-600">Start a session to retrieve its history.</p> : null}
        <ul className="mt-3 space-y-2">
          {sessions.map((session) => (
            <li key={session.id}>
              <button
                type="button"
                onClick={() => onHistory(session.id)}
                disabled={pending !== null}
                className="rounded border border-stone-400 px-3 py-2 text-sm disabled:opacity-50"
              >
                History for {session.topic_title}
              </button>
            </li>
          ))}
        </ul>
        {history ? (
          <div className="mt-4 text-sm" aria-live="polite">
            <p className="font-medium">{history.topic_title}</p>
            <p className="text-stone-600">{history.knowledge.length} knowledge records for this topic.</p>
            <ul className="mt-2 space-y-2">
              {history.knowledge.map((item) => (
                <li key={item.id}>
                  {item.concept}: {item.summary}{" "}
                  <span className="text-stone-500">{evidenceLabel(item.evidence_kind)}</span>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-stone-600">{history.assessments.length} assessment notes.</p>
          </div>
        ) : null}
      </div>
    </section>
  );
}

function KnowledgeItem({ item, topicTitle }: { item: KnowledgeRecord; topicTitle?: string }) {
  return (
    <li className="rounded border border-stone-200 px-3 py-2 text-sm">
      <p className="font-medium">
        {item.concept}
        {topicTitle ? <span className="font-normal text-stone-500"> · {topicTitle}</span> : null}
      </p>
      <p>{item.summary}</p>
      <p className="text-stone-600">
        <span>{evidenceLabel(item.evidence_kind)}</span>
        <span> · confidence {item.confidence.toFixed(2)}</span>
      </p>
    </li>
  );
}
