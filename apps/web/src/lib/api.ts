import { writeLog } from "./logger";

export class ApiError extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;

  constructor(status: number, code: string, message: string, requestId: string | null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
  }
}

export type Learner = {
  id: string;
  display_name: string;
  created_at: string;
  updated_at: string;
};

export type Topic = {
  id: string;
  title: string;
  slug: string;
  description: string | null;
  created_at: string;
};

export type LearningSession = {
  id: string;
  learner_id: string;
  topic_id: string;
  learner_name: string;
  topic_title: string;
  topic_slug: string;
  status: string;
  created_at: string;
  updated_at: string;
  resumed_at: string | null;
};

export type Health = {
  status: string;
  database: string;
};

export type Account = {
  user_id: string;
  email: string;
  learner_id: string;
  display_name: string;
  created_at: string;
};

type ErrorBody = {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
    details?: { field?: string; message?: string }[];
  };
};

export type UiError = {
  code: string;
  message: string;
  requestId: string | null;
};

export function toUiError(error: unknown): UiError {
  if (error instanceof ApiError) {
    writeLog("warn", "api_error", {
      code: error.code,
      status: error.status,
      requestId: error.requestId,
    });
    return { code: error.code, message: error.message, requestId: error.requestId };
  }
  writeLog("error", "unexpected_client_error", {
    errorType: error instanceof Error ? error.name : "Error",
  });
  return {
    code: "unexpected_error",
    message: "Something went wrong. Try again.",
    requestId: null,
  };
}

export async function parseApiError(response: Response, fallbackRequestId: string): Promise<ApiError> {
  const requestId = response.headers.get("x-request-id") ?? fallbackRequestId;
  let body: ErrorBody | null = null;
  try {
    body = (await response.json()) as ErrorBody;
  } catch {
    body = null;
  }
  const detail = body?.error?.details?.find((item) => item.field && item.message);
  const message = body?.error?.message ?? "The request could not be completed.";
  const fullMessage = detail ? `${message} ${detail.field}: ${detail.message}` : message;
  return new ApiError(response.status, body?.error?.code ?? "http_error", fullMessage, body?.error?.request_id ?? requestId);
}

export async function apiRequest<T>(path: string, init?: RequestInit): Promise<T> {
  const requestId = crypto.randomUUID();
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      credentials: init?.credentials ?? "include",
      headers: {
        accept: "application/json",
        "content-type": "application/json",
        "x-request-id": requestId,
        ...(init?.headers ?? {}),
      },
      cache: "no-store",
      signal: init?.signal ?? AbortSignal.timeout(10_000),
    });
  } catch (error) {
    const timedOut = error instanceof Error && (error.name === "TimeoutError" || error.name === "AbortError");
    throw new ApiError(
      0,
      timedOut ? "timeout" : "network_error",
      timedOut ? "The request timed out." : "The server could not be reached.",
      requestId,
    );
  }

  if (!response.ok) {
    throw await parseApiError(response, requestId);
  }
  try {
    return (await response.json()) as T;
  } catch {
    throw new ApiError(
      response.status,
      "invalid_response",
      "The server returned an unreadable response.",
      response.headers.get("x-request-id") ?? requestId,
    );
  }
}

export function getHealth(): Promise<Health> {
  return apiRequest<Health>("/health");
}

export function currentAccount(): Promise<Account> {
  return apiRequest<Account>("/api/auth/me");
}

export function signupAccount(displayName: string, email: string, password: string): Promise<Account> {
  return apiRequest<Account>("/api/auth/signup", {
    method: "POST",
    body: JSON.stringify({ display_name: displayName, email, password }),
  });
}

export function signinAccount(email: string, password: string): Promise<Account> {
  return apiRequest<Account>("/api/auth/signin", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export function signOut(): Promise<{ status: string }> {
  return apiRequest<{ status: string }>("/api/auth/signout", { method: "POST" });
}

export function createLearner(displayName: string): Promise<Learner> {
  return apiRequest<Learner>("/api/learners", {
    method: "POST",
    body: JSON.stringify({ display_name: displayName }),
  });
}

export function listLearners(): Promise<Learner[]> {
  return apiRequest<Learner[]>("/api/learners");
}

export function createTopic(title: string, slug: string, description: string): Promise<Topic> {
  return apiRequest<Topic>("/api/topics", {
    method: "POST",
    body: JSON.stringify({
      title,
      slug,
      description: description.trim() ? description.trim() : null,
    }),
  });
}

export function listTopics(): Promise<Topic[]> {
  return apiRequest<Topic[]>("/api/topics");
}

export function createSession(learnerId: string, topicId: string): Promise<LearningSession> {
  return apiRequest<LearningSession>("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ learner_id: learnerId, topic_id: topicId }),
  });
}

export function listSessions(): Promise<LearningSession[]> {
  return apiRequest<LearningSession[]>("/api/sessions");
}

export function resumeSession(sessionId: string): Promise<LearningSession> {
  return apiRequest<LearningSession>(`/api/sessions/${sessionId}/resume`, { method: "POST" });
}

export type EvidenceKind = "observed" | "inferred";

export type LearnerProfileDetail = {
  id: string;
  display_name: string;
  background_note: string | null;
  created_at: string;
  updated_at: string;
};

export type LearningPreference = {
  pace: "unhurried" | "steady" | "intensive";
  explanation_detail: "concise" | "balanced" | "thorough";
  practice_first: boolean;
  notes: string | null;
  updated_at: string;
};

export type LearningGoal = {
  id: string;
  topic_id: string | null;
  statement: string;
  status: "active" | "completed" | "archived";
  created_at: string;
  updated_at: string;
};

export type KnowledgeRecord = {
  id: string;
  topic_id: string;
  concept: string;
  summary: string;
  evidence_kind: EvidenceKind;
  provenance: string;
  confidence: number;
  confirmed: boolean;
  correction_note: string | null;
  corrected_at: string | null;
  replaces_id: string | null;
  created_at: string;
};

export type MisconceptionRecord = {
  id: string;
  topic_id: string;
  concept: string;
  description: string;
  evidence_kind: EvidenceKind;
  provenance: string;
  confidence: number;
  confirmed: boolean;
  supporting_note: string | null;
  status: "open" | "resolved" | "rejected";
  correction_note: string | null;
  corrected_at: string | null;
  replaces_id: string | null;
  created_at: string;
};

export type AssessmentRecord = {
  id: string;
  topic_id: string;
  session_id: string | null;
  prompt_summary: string;
  response_summary: string;
  outcome: "recorded" | "correct" | "partial" | "incorrect" | "unanswered";
  created_at: string;
};

export type LearningActivityRecord = {
  id: string;
  topic_id: string | null;
  session_id: string | null;
  activity_kind: "explanation" | "practice" | "review" | "note";
  summary: string;
  occurred_at: string;
  created_at: string;
};

export type LearnerDashboardData = {
  profile: LearnerProfileDetail;
  preferences: LearningPreference | null;
  goals: LearningGoal[];
  knowledge: KnowledgeRecord[];
  misconceptions: MisconceptionRecord[];
  assessments: AssessmentRecord[];
  activities: LearningActivityRecord[];
};

export type SessionHistory = {
  session_id: string;
  learner_id: string;
  topic_id: string;
  topic_title: string;
  profile: LearnerProfileDetail;
  preferences: LearningPreference | null;
  goals: LearningGoal[];
  knowledge: KnowledgeRecord[];
  misconceptions: MisconceptionRecord[];
  assessments: AssessmentRecord[];
  activities: LearningActivityRecord[];
};

export function getLearnerDashboard(): Promise<LearnerDashboardData> {
  return apiRequest<LearnerDashboardData>("/api/learner");
}

export function updateLearnerProfile(displayName: string, backgroundNote: string): Promise<LearnerProfileDetail> {
  return apiRequest<LearnerProfileDetail>("/api/learner/profile", {
    method: "PATCH",
    body: JSON.stringify({
      display_name: displayName,
      background_note: backgroundNote.trim() ? backgroundNote.trim() : "",
    }),
  });
}

export function saveLearnerPreferences(
  pace: LearningPreference["pace"],
  explanationDetail: LearningPreference["explanation_detail"],
  practiceFirst: boolean,
  notes: string,
): Promise<LearningPreference> {
  return apiRequest<LearningPreference>("/api/learner/preferences", {
    method: "PUT",
    body: JSON.stringify({
      pace,
      explanation_detail: explanationDetail,
      practice_first: practiceFirst,
      notes: notes.trim() ? notes.trim() : null,
    }),
  });
}

export function createLearningGoal(statement: string, topicId: string): Promise<LearningGoal> {
  return apiRequest<LearningGoal>("/api/learner/goals", {
    method: "POST",
    body: JSON.stringify({
      statement,
      topic_id: topicId || null,
    }),
  });
}

export function recordKnowledge(topicId: string, concept: string, summary: string, confidence: number): Promise<KnowledgeRecord> {
  return apiRequest<KnowledgeRecord>("/api/learner/knowledge", {
    method: "POST",
    body: JSON.stringify({
      topic_id: topicId,
      concept,
      summary,
      evidence_kind: "inferred",
      provenance: "learner_report",
      confidence,
    }),
  });
}

export function correctKnowledge(knowledgeId: string, summary: string, correctionNote: string): Promise<KnowledgeRecord> {
  return apiRequest<KnowledgeRecord>(`/api/learner/knowledge/${knowledgeId}`, {
    method: "PATCH",
    body: JSON.stringify({ summary, correction_note: correctionNote }),
  });
}

export function recordAssessment(
  topicId: string,
  promptSummary: string,
  responseSummary: string,
): Promise<AssessmentRecord> {
  return apiRequest<AssessmentRecord>("/api/learner/assessments", {
    method: "POST",
    body: JSON.stringify({
      topic_id: topicId,
      prompt_summary: promptSummary,
      response_summary: responseSummary,
      outcome: "recorded",
    }),
  });
}

export function recordMisconception(
  topicId: string,
  concept: string,
  description: string,
  supportingNote: string,
): Promise<MisconceptionRecord> {
  return apiRequest<MisconceptionRecord>("/api/learner/misconceptions", {
    method: "POST",
    body: JSON.stringify({
      topic_id: topicId,
      concept,
      description,
      evidence_kind: "inferred",
      provenance: "learner_report",
      confidence: 0.4,
      supporting_note: supportingNote.trim() ? supportingNote.trim() : null,
    }),
  });
}

export function recordActivity(
  topicId: string,
  activityKind: LearningActivityRecord["activity_kind"],
  summary: string,
): Promise<LearningActivityRecord> {
  return apiRequest<LearningActivityRecord>("/api/learner/activities", {
    method: "POST",
    body: JSON.stringify({
      topic_id: topicId || null,
      activity_kind: activityKind,
      summary,
    }),
  });
}

export function getSessionHistory(sessionId: string): Promise<SessionHistory> {
  return apiRequest<SessionHistory>(`/api/sessions/${sessionId}/history`);
}

export type LearningObjectiveRecord = {
  id: string;
  topic_id: string;
  code: string;
  statement: string;
  concept: string;
  position: number;
  prerequisite_codes: string[];
  created_at: string;
};

export type DiagnosisQuestion = {
  id: string;
  objective_code: string;
  objective_statement: string;
  concept: string;
  format: "short_answer" | "multiple_choice" | "reasoning";
  prompt: string;
  choices: string[] | null;
  position: number;
};

export type DiagnosisJudgment = {
  question_id: string;
  objective_code: string;
  answer_text: string;
  reasoning_text: string;
  answer_verdict: "correct" | "partial" | "incorrect" | "unanswered";
  reasoning_verdict: "sound" | "partial" | "weak" | "absent" | "uncertain";
  understanding: "none" | "partial" | "solid" | "uncertain";
  confidence: number;
  needs_review: boolean;
  confirmed: boolean;
};

export type DiagnosisMisconception = {
  id: string;
  concept: string;
  description: string;
  evidence: string | null;
  confidence: number;
  confirmed: boolean;
};

export type DiagnosisReport = {
  id: string;
  session_id: string;
  topic_id: string;
  status: "in_progress" | "completed";
  session_status: string;
  starting_point: "beginner" | "partial" | "uncertain" | null;
  confidence: number | null;
  summary: string | null;
  first_unmet_objective_code: string | null;
  questions: DiagnosisQuestion[];
  judgments: DiagnosisJudgment[];
  misconceptions: DiagnosisMisconception[];
};

export function createLearningObjective(
  topicId: string,
  code: string,
  statement: string,
  concept: string,
  prerequisiteCodes: string[],
): Promise<LearningObjectiveRecord> {
  return apiRequest<LearningObjectiveRecord>(`/api/topics/${topicId}/objectives`, {
    method: "POST",
    body: JSON.stringify({
      code,
      statement,
      concept,
      prerequisite_codes: prerequisiteCodes,
    }),
  });
}

export function startDiagnosis(sessionId: string): Promise<DiagnosisReport> {
  return apiRequest<DiagnosisReport>(`/api/sessions/${sessionId}/diagnosis`, { method: "POST" });
}

export function getDiagnosis(sessionId: string): Promise<DiagnosisReport> {
  return apiRequest<DiagnosisReport>(`/api/sessions/${sessionId}/diagnosis`);
}

export function submitDiagnosis(
  sessionId: string,
  responses: { question_id: string; answer_text: string; reasoning_text: string }[],
): Promise<DiagnosisReport> {
  return apiRequest<DiagnosisReport>(`/api/sessions/${sessionId}/diagnosis/responses`, {
    method: "POST",
    body: JSON.stringify({ responses }),
  });
}

export function listLearningObjectives(topicId: string): Promise<LearningObjectiveRecord[]> {
  return apiRequest<LearningObjectiveRecord[]>(`/api/topics/${topicId}/objectives`);
}

export function addObjectivePrerequisite(topicId: string, objectiveId: string, prerequisiteCode: string): Promise<LearningObjectiveRecord> {
  return apiRequest<LearningObjectiveRecord>(`/api/topics/${topicId}/objectives/${objectiveId}/prerequisites`, {
    method: "POST",
    body: JSON.stringify({ prerequisite_code: prerequisiteCode }),
  });
}

export function startFollowUp(sessionId: string): Promise<DiagnosisReport> {
  return apiRequest<DiagnosisReport>(`/api/sessions/${sessionId}/diagnosis/follow-up`, { method: "POST" });
}

export type PlanConcept = {
  id: string;
  topic_id: string;
  name: string;
  position: number;
  summary: string;
};

export type PlanStep = {
  id: string;
  position: number;
  objective_id: string;
  objective_code: string;
  objective_statement: string;
  concept_id: string;
  concept: string;
  status: "satisfied" | "current" | "upcoming";
  evidence: "observed" | "none";
  completion_criteria: string;
};

export type LearningPlan = {
  id: string;
  session_id: string;
  topic_id: string;
  revision: number;
  status: "active" | "superseded";
  session_status: string;
  diagnostic_attempt_id: string;
  starting_objective_code: string | null;
  summary: string;
  current_step_id: string | null;
  concepts: PlanConcept[];
  steps: PlanStep[];
  created_at: string;
  updated_at: string;
};

export function createLearningPlan(sessionId: string): Promise<LearningPlan> {
  return apiRequest<LearningPlan>(`/api/sessions/${sessionId}/plan`, { method: "POST" });
}

export function getLearningPlan(sessionId: string): Promise<LearningPlan> {
  return apiRequest<LearningPlan>(`/api/sessions/${sessionId}/plan`);
}

export function reviseLearningPlan(sessionId: string): Promise<LearningPlan> {
  return apiRequest<LearningPlan>(`/api/sessions/${sessionId}/plan/revision`, { method: "POST" });
}

export type PedagogySelection = {
  id: string;
  session_id: string;
  revision: number;
  status: string;
  session_status: string;
  policy_version: string;
  registry_version: string;
  situation: string;
  primary_strategy: string | null;
  supporting_strategies: string[];
  sequence: string[];
  success_signals: string[];
  fallback_strategy: string | null;
  rationale: string;
  controls_teaching: boolean;
  production_primary_strategy: string | null;
  created_at: string;
};

export function chooseStrategies(sessionId: string): Promise<PedagogySelection> {
  return apiRequest<PedagogySelection>(`/api/sessions/${sessionId}/pedagogy-selection`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getStrategySelection(sessionId: string): Promise<PedagogySelection> {
  return apiRequest<PedagogySelection>(`/api/sessions/${sessionId}/pedagogy-selection`);
}

export type TeachingHint = {
  position: number;
  text: string;
};

export type TeachingActivity = {
  id: string;
  position: number;
  strategy_id: string;
  kind: string;
  title: string;
  prompt: string;
  example: string | null;
  worked_steps: string[];
  support_level: string;
  status: string;
  hints_available: number;
  hints_revealed: TeachingHint[];
  inserted_for_struggle: boolean;
};

export type TeachingLesson = {
  id: string;
  session_id: string;
  selection_id: string;
  objective_code: string;
  status: string;
  session_status: string;
  review_status: string;
  strategy_ids: string[];
  current_activity_id: string | null;
  activities: TeachingActivity[];
  created_at: string;
  updated_at: string;
};

export function startLesson(sessionId: string): Promise<TeachingLesson> {
  return apiRequest<TeachingLesson>(`/api/sessions/${sessionId}/teaching`, { method: "POST" });
}

export function getLesson(sessionId: string): Promise<TeachingLesson> {
  return apiRequest<TeachingLesson>(`/api/sessions/${sessionId}/teaching`);
}

export function revealHint(sessionId: string): Promise<TeachingLesson> {
  return apiRequest<TeachingLesson>(`/api/sessions/${sessionId}/teaching/hint`, { method: "POST" });
}

export function submitTeachingAttempt(
  sessionId: string,
  outcome: "correct" | "incorrect" | "struggled",
  answerText: string,
): Promise<TeachingLesson> {
  return apiRequest<TeachingLesson>(`/api/sessions/${sessionId}/teaching/attempt`, {
    method: "POST",
    body: JSON.stringify({ outcome, answer_text: answerText }),
  });
}

export type EvaluationAttempt = {
  id: string;
  session_id: string;
  revision: number;
  status: string;
  session_status: string;
  objective_code: string;
  prompt: string;
  rubric: string[];
  decision: string | null;
  credit: string | null;
  feedback: string | null;
  answer_verdict: string | null;
  reasoning_verdict: string | null;
  understanding: string | null;
  remediation_strategy: string | null;
  misconception_evidence: string | null;
  created_at: string;
  updated_at: string;
};

export function startEvaluation(sessionId: string): Promise<EvaluationAttempt> {
  return apiRequest<EvaluationAttempt>(`/api/sessions/${sessionId}/evaluation`, { method: "POST" });
}

export function getEvaluation(sessionId: string): Promise<EvaluationAttempt> {
  return apiRequest<EvaluationAttempt>(`/api/sessions/${sessionId}/evaluation`);
}

export function submitEvaluation(
  sessionId: string,
  answerText: string,
  reasoningText: string,
): Promise<EvaluationAttempt> {
  return apiRequest<EvaluationAttempt>(`/api/sessions/${sessionId}/evaluation/response`, {
    method: "POST",
    body: JSON.stringify({ answer_text: answerText, reasoning_text: reasoningText }),
  });
}

export function startRemediation(sessionId: string): Promise<EvaluationAttempt> {
  return apiRequest<EvaluationAttempt>(`/api/sessions/${sessionId}/evaluation/remediation`, { method: "POST" });
}

export type RevisionReview = {
  id: string;
  session_id: string;
  objective_code: string;
  interval_index: number;
  due_on: string;
  timezone: string;
  status: string;
  timing: string;
  was_missed: boolean;
  outcome: string | null;
  session_status: string;
  prompt: string | null;
  rubric: string[];
  created_at: string;
  updated_at: string;
};

export function listReviews(): Promise<RevisionReview[]> {
  return apiRequest<RevisionReview[]>("/api/retention");
}

export function startReview(sessionId: string): Promise<RevisionReview> {
  return apiRequest<RevisionReview>(`/api/sessions/${sessionId}/retention`, { method: "POST" });
}

export function submitReview(sessionId: string, answerText: string, reasoningText: string): Promise<RevisionReview> {
  return apiRequest<RevisionReview>(`/api/sessions/${sessionId}/retention/response`, {
    method: "POST",
    body: JSON.stringify({ answer_text: answerText, reasoning_text: reasoningText }),
  });
}
