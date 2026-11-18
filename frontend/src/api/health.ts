import type { components } from "./schema";

export type ApiHealth = "ok" | "unreachable";

type HealthBody = { status: "ok" };

/** Calls `getHealth` (GET /health) of the SAPS API through the same-origin proxy. */
export async function fetchApiHealth(fetchImpl: typeof fetch = fetch): Promise<ApiHealth> {
  try {
    const response = await fetchImpl("/health");
    if (!response.ok) return "unreachable";
    const body = (await response.json()) as HealthBody;
    return body.status === "ok" ? "ok" : "unreachable";
  } catch {
    return "unreachable";
  }
}

/** Re-exported so feature code uses the generated contract types (`npm run gen:api`). */
export type Schemas = components["schemas"];
