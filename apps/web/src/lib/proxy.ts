import { writeLog } from "./logger";

export const MAX_PROXY_BODY_BYTES = 65_536;
const DEFAULT_TIMEOUT_MS = 10_000;

export type FetchLike = (input: string, init?: RequestInit) => Promise<Response>;

export function upstreamUrl(target: string, path: string, search: string): string {
  return `${target.replace(/\/$/, "")}${path}${search}`;
}

class PayloadTooLarge extends Error {
  constructor() {
    super("The request body is too large.");
    this.name = "PayloadTooLarge";
  }
}

async function readBody(request: Request, maxBytes: number): Promise<string | undefined> {
  const method = request.method.toUpperCase();
  if (method === "GET" || method === "HEAD") {
    return undefined;
  }
  const declared = Number(request.headers.get("content-length") ?? "");
  if (Number.isFinite(declared) && declared > maxBytes) {
    throw new PayloadTooLarge();
  }
  if (!request.body) {
    return "";
  }

  const reader = request.body.getReader();
  const chunks: Uint8Array[] = [];
  let received = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) {
      break;
    }
    received += value.byteLength;
    if (received > maxBytes) {
      await reader.cancel();
      throw new PayloadTooLarge();
    }
    chunks.push(value);
  }

  const merged = new Uint8Array(received);
  let offset = 0;
  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return new TextDecoder().decode(merged);
}

function requestIdFor(request: Request): string {
  const incoming = request.headers.get("x-request-id")?.trim() ?? "";
  if (!incoming || incoming.length > 128 || /[\u0000-\u001f\u007f]/.test(incoming)) {
    return crypto.randomUUID();
  }
  return incoming;
}

function unavailable(code: string, message: string, requestId: string): Response {
  return Response.json(
    { error: { code, message, request_id: requestId } },
    { status: 503, headers: { "x-request-id": requestId } },
  );
}

export async function proxyRequest(
  request: Request,
  path: string,
  options?: { target?: string; fetchImpl?: FetchLike; timeoutMs?: number },
): Promise<Response> {
  const target = options?.target ?? process.env.API_PROXY_TARGET ?? "http://127.0.0.1:8000";
  const fetchImpl = options?.fetchImpl ?? fetch;
  const timeoutMs = options?.timeoutMs ?? DEFAULT_TIMEOUT_MS;
  const requestId = requestIdFor(request);
  const method = request.method.toUpperCase();
  const started = Date.now();
  const url = upstreamUrl(target, path, new URL(request.url).search);

  try {
    const body = await readBody(request, MAX_PROXY_BODY_BYTES);
    const headers: Record<string, string> = {
      accept: request.headers.get("accept") ?? "application/json",
      "content-type": request.headers.get("content-type") ?? "application/json",
      "x-request-id": requestId,
    };
    const cookie = request.headers.get("cookie");
    if (cookie) {
      headers.cookie = cookie;
    }
    const upstream = await fetchImpl(url, {
      method,
      headers,
      body,
      cache: "no-store",
      signal: AbortSignal.timeout(timeoutMs),
    });
    const responseBody = await upstream.arrayBuffer();
    writeLog(upstream.status >= 500 ? "error" : "info", "proxy_completed", {
      requestId,
      method,
      path,
      statusCode: upstream.status,
      durationMs: Date.now() - started,
    });
    const responseHeaders = new Headers();
    responseHeaders.set("content-type", upstream.headers.get("content-type") ?? "application/json");
    responseHeaders.set("x-request-id", upstream.headers.get("x-request-id") ?? requestId);
    const setCookies =
      typeof upstream.headers.getSetCookie === "function" ? upstream.headers.getSetCookie() : [];
    if (setCookies.length > 0) {
      for (const setCookie of setCookies) {
        responseHeaders.append("set-cookie", setCookie);
      }
    } else {
      const setCookie = upstream.headers.get("set-cookie");
      if (setCookie) {
        responseHeaders.append("set-cookie", setCookie);
      }
    }
    return new Response(responseBody, {
      status: upstream.status,
      headers: responseHeaders,
    });
  } catch (error) {
    if (error instanceof PayloadTooLarge) {
      writeLog("warn", "proxy_rejected", { requestId, method, path, code: "payload_too_large" });
      return Response.json(
        {
          error: {
            code: "payload_too_large",
            message: "The request body is too large.",
            request_id: requestId,
          },
        },
        { status: 413, headers: { "x-request-id": requestId } },
      );
    }
    const timedOut = error instanceof Error && (error.name === "TimeoutError" || error.name === "AbortError");
    writeLog("error", "proxy_failed", {
      requestId,
      method,
      path,
      errorType: timedOut ? "timeout" : "network",
      durationMs: Date.now() - started,
    });
    return unavailable(
      timedOut ? "timeout" : "upstream_unavailable",
      timedOut ? "The API did not respond in time." : "The API could not be reached.",
      requestId,
    );
  }
}
