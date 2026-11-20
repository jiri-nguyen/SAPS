import { vi } from "vitest";

import type { MatchingSettings, SettingsApi } from "../api/settings";

/** The defaults created by the seed (SAPS-27): 0.5 USD and 300 USD, last changed by `system`. */
export function settingsFixture(overrides: Partial<MatchingSettings> = {}): MatchingSettings {
  return {
    priceToleranceUsd: "0.5000",
    approvalThresholdUsd: "300.00",
    updatedAt: "2026-12-01T08:00:00Z",
    updatedBy: "system",
    ...overrides,
  };
}

export function fakeSettingsApi(overrides: Partial<SettingsApi> = {}): SettingsApi {
  return {
    get: vi.fn().mockResolvedValue(settingsFixture()),
    update: vi.fn().mockResolvedValue(settingsFixture()),
    ...overrides,
  };
}
