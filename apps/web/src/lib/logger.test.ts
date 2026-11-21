import { describe, expect, it } from "vitest";

import { formatLog, redactText } from "./logger";

describe("logger", () => {
  it("redacts connection strings, bearer tokens, and API keys", () => {
    const redacted = redactText(
      "postgresql+psycopg://ai_teacher:supersecret@db/ai_teacher Bearer secret-token AIzaSyA1234567890abcdefghij",
    );
    expect(redacted).not.toContain("supersecret");
    expect(redacted).not.toContain("secret-token");
    expect(redacted).not.toContain("AIzaSyA1234567890abcdefghij");
  });

  it("redacts sensitive fields before writing a log line", () => {
    const line = formatLog("error", "proxy_failed", {
      authorization: "Bearer secret-token",
      path: "/api/learners",
    });
    expect(line).toContain("proxy_failed");
    expect(line).toContain("/api/learners");
    expect(line).not.toContain("secret-token");
    expect(line).toContain("[redacted]");
  });
});
