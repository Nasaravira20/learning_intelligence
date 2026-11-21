const SENSITIVE_KEY = /password|secret|token|authorization|cookie|api[_-]?key|database[_-]?url/i;
const SENSITIVE_TEXT = /postgresql(?:\+\w+)?:\/\/\S+|bearer\s+\S+|AIza[0-9A-Za-z\-_]{20,}/gi;

export type LogLevel = "info" | "warn" | "error";

export function redactText(value: string): string {
  return value.replace(SENSITIVE_TEXT, "[redacted]");
}

export function redactValue(key: string, value: unknown): unknown {
  if (SENSITIVE_KEY.test(key)) {
    return "[redacted]";
  }
  if (typeof value === "string") {
    return redactText(value);
  }
  if (Array.isArray(value)) {
    return value.map((item) => redactValue(key, item));
  }
  if (value && typeof value === "object") {
    return redactFields(value as Record<string, unknown>);
  }
  return value;
}

export function redactFields(fields: Record<string, unknown>): Record<string, unknown> {
  const cleaned: Record<string, unknown> = {};
  for (const [key, value] of Object.entries(fields)) {
    cleaned[key] = redactValue(key, value);
  }
  return cleaned;
}

export function formatLog(level: LogLevel, event: string, fields: Record<string, unknown> = {}): string {
  return JSON.stringify({
    timestamp: new Date().toISOString(),
    level,
    event,
    ...redactFields(fields),
  });
}

export function writeLog(level: LogLevel, event: string, fields: Record<string, unknown> = {}): void {
  const line = formatLog(level, event, fields);
  if (level === "error") {
    console.error(line);
    return;
  }
  if (level === "warn") {
    console.warn(line);
    return;
  }
  console.log(line);
}
