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
