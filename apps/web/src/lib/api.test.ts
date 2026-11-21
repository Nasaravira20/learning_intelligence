import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, apiRequest, parseApiError, toUiError } from "./api";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("api client", () => {
  it("turns an error envelope into an ApiError", async () => {
    const response = new Response(
      JSON.stringify({
        error: {
          code: "learner_not_found",
          message: "Learner was not found.",
          request_id: "req-1",
        },
      }),
      { status: 404, headers: { "content-type": "application/json", "x-request-id": "req-1" } },
    );

    const error = await parseApiError(response, "fallback");
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("learner_not_found");
    expect(error.requestId).toBe("req-1");
    expect(error.message).toBe("Learner was not found.");
  });

  it("includes the first field detail on validation errors", async () => {
    const response = new Response(
      JSON.stringify({
        error: {
          code: "validation_error",
          message: "The request was invalid.",
          request_id: "req-2",
          details: [{ field: "display_name", message: "Display name is required." }],
        },
      }),
      { status: 422, headers: { "x-request-id": "req-2" } },
    );
    const error = await parseApiError(response, "fallback");
    expect(error.message).toContain("display_name");
    expect(error.message).toContain("Display name is required.");
  });

  it("reports a network failure without throwing a raw fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      throw new TypeError("failed to fetch");
    }));
    await expect(apiRequest("/health")).rejects.toMatchObject({
      code: "network_error",
      message: "The server could not be reached.",
    });
  });

  it("reports a timeout", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => {
      const error = new Error("timed out");
      error.name = "TimeoutError";
      throw error;
    }));
    await expect(apiRequest("/health")).rejects.toMatchObject({ code: "timeout" });
  });

  it("hides unexpected error details from the interface", () => {
    const shown = toUiError(new Error("postgresql+psycopg://ai_teacher:supersecret@db/ai_teacher"));
    expect(shown.code).toBe("unexpected_error");
    expect(shown.message).toBe("Something went wrong. Try again.");
    expect(shown.message).not.toContain("supersecret");
  });
});
