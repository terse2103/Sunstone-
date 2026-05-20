const RAW_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const API_BASE_URL = RAW_BASE.replace(/\/+$/, "");

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, message: string, detail?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

interface RequestOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

export async function request<T>(
  path: string,
  { method = "GET", body, signal }: RequestOptions = {},
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const headers: Record<string, string> = { Accept: "application/json" };
  let init: RequestInit = { method, headers, signal };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    init = { ...init, body: JSON.stringify(body) };
  }

  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err) {
    if ((err as { name?: string }).name === "AbortError") throw err;
    throw new ApiError(0, "network_error", err);
  }

  if (res.status === 204) return undefined as T;

  const text = await res.text();
  const parsed = text ? safeJson(text) : undefined;

  if (!res.ok) {
    const detail = extractDetail(parsed) ?? res.statusText;
    throw new ApiError(res.status, String(detail), parsed);
  }

  return parsed as T;
}

function safeJson(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function extractDetail(parsed: unknown): string | undefined {
  if (parsed && typeof parsed === "object" && "detail" in parsed) {
    const detail = (parsed as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    return JSON.stringify(detail);
  }
  return undefined;
}
