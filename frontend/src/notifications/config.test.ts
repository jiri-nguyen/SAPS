import { describe, expect, it } from "vitest";

import { DEFAULT_POLL_SECONDS, pollIntervalMs } from "./config";

describe("notification polling interval (SAPS-24 §3.8)", () => {
  it("is 15 seconds unless the build sets another valid value", () => {
    expect(DEFAULT_POLL_SECONDS).toBe(15);
    expect(pollIntervalMs(undefined)).toBe(15_000);
    expect(pollIntervalMs("5")).toBe(5_000);
    expect(pollIntervalMs("0.5")).toBe(500);
  });

  it.each(["", "abc", "0", "-3", "Infinity"])("falls back to the default for %j", (raw) => {
    expect(pollIntervalMs(raw)).toBe(15_000);
  });
});
