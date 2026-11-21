import { describe, expect, it, vi } from "vitest";

import { proxyRequest, upstreamUrl } from "./proxy";

describe("proxy", () => {
  it("builds an upstream URL without a trailing slash on the target", () => {
    expect(upstreamUrl("http://api:8000/", "/health", "?ready=1")).toBe("http://api:8000/health?ready=1");
  });

  it("forwards the session cookie, drops authorization, and copies Set-Cookie", async () => {
    let captured: RequestInit | undefined;
    const fetchImpl = vi.fn(async (_url: string, init?: RequestInit) => {
      captured = init;
      return new Response(JSON.stringify({ status: "ok" }), {
        status: 200,
        headers: {
          "content-type": "application/json",
          "x-request-id": "req-proxy",
          "set-cookie": "ai_teacher_session=issued-token; HttpOnly; Path=/",
        },
      });
    });
    const request = new Request("http://localhost:3000/api/auth/me", {
      headers: {
        authorization: "Bearer secret-token",
        cookie: "ai_teacher_session=browser-token",
        "x-request-id": "req-proxy",
      },
    });

    const response = await proxyRequest(request, "/api/auth/me", {
      target: "http://api:8000",
      fetchImpl,
    });

    const forwarded = captured?.headers as Record<string, string>;
    expect(response.status).toBe(200);
    expect(forwarded.cookie).toBe("ai_teacher_session=browser-token");
    expect(JSON.stringify(forwarded)).not.toContain("secret-token");
    expect(response.headers.get("set-cookie")).toContain("ai_teacher_session=issued-token");
    expect(response.headers.get("x-request-id")).toBe("req-proxy");
  });

  it("returns a JSON envelope when the API cannot be reached", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new TypeError("connect ECONNREFUSED");
    });
    const request = new Request("http://localhost:3000/api/learners", {
      method: "POST",
      headers: { "content-type": "application/json", "x-request-id": "req-down" },
      body: JSON.stringify({ display_name: "Ada" }),
    });

    const response = await proxyRequest(request, "/api/learners", {
      target: "http://api:8000",
      fetchImpl,
    });
    const body = await response.json();

    expect(response.status).toBe(503);
    expect(body.error.code).toBe("upstream_unavailable");
    expect(body.error.request_id).toBe("req-down");
    expect(JSON.stringify(body)).not.toContain("Ada");
  });

  it("rejects an oversized body before calling the API", async () => {
    const fetchImpl = vi.fn();
    const request = new Request("http://localhost:3000/api/learners", {
      method: "POST",
      body: "x".repeat(70_000),
      headers: { "x-request-id": "req-big" },
    });

    const response = await proxyRequest(request, "/api/learners", {
      target: "http://api:8000",
      fetchImpl,
    });

    expect(response.status).toBe(413);
    expect(fetchImpl).not.toHaveBeenCalled();
    expect((await response.json()).error.code).toBe("payload_too_large");
  });
});
