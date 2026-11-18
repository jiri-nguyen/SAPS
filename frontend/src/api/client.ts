import type { components } from "./schema";

export type Problem = components["schemas"]["Problem"];

/** An error answer of the SAPS API (RFC 9457 problem details). */
export class ApiError extends Error {
  readonly status: number;
  readonly problem: Problem | undefined;

  constructor(status: number, problem?: Problem) {
    super(problem?.detail ?? problem?.title ?? `HTTP ${status}`);
    this.name = "ApiError";
    this.status = status;
    this.problem = problem;
  }
}

/** Fired on every 401 so the Web App returns to the sign-in page (SAPS-27 BR-10). */
export const unauthorizedEvents = new EventTarget();
export const UNAUTHORIZED = "unauthorized";

async function readProblem(response: Response): Promise<Problem | undefined> {
  try {
    return (await response.json()) as Problem;
  } catch {
    return undefined;
  }
}

/**
 * Calls the SAPS API on the same origin. The browser sends the session cookie and,
 * for POST/PUT/PATCH/DELETE, the Origin header that the API checks (ADR-0008).
 */
export async function apiFetch(
  path: string,
  init: RequestInit = {},
  fetchImpl: typeof fetch = fetch,
): Promise<Response> {
  const headers = new Headers(init.headers);
  headers.set("Accept", "application/json");
  if (init.body !== undefined) headers.set("Content-Type", "application/json");
  const response = await fetchImpl(path, { ...init, headers, credentials: "same-origin" });
  if (response.ok) return response;
  if (response.status === 401) unauthorizedEvents.dispatchEvent(new Event(UNAUTHORIZED));
  throw new ApiError(response.status, await readProblem(response));
}
