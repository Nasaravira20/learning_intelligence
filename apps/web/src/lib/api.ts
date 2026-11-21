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
