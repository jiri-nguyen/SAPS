import { apiFetch } from "./client";
import type { components } from "./schema";

export type MatchingSettings = components["schemas"]["MatchingSettings"];
export type MatchingSettingsUpdate = components["schemas"]["MatchingSettingsUpdate"];

/** Matching settings operations of the SAPS API (SAPS-28); Accounting Managers only. */
export interface SettingsApi {
  get(): Promise<MatchingSettings>;
  update(body: MatchingSettingsUpdate): Promise<MatchingSettings>;
}

export function createSettingsApi(fetchImpl: typeof fetch = fetch): SettingsApi {
  return {
    async get() {
      const response = await apiFetch("/v1/matching-settings", {}, fetchImpl);
      return (await response.json()) as MatchingSettings;
    },
    async update(body) {
      const response = await apiFetch(
        "/v1/matching-settings",
        { method: "PUT", body: JSON.stringify(body) },
        fetchImpl,
      );
      return (await response.json()) as MatchingSettings;
    },
  };
}
