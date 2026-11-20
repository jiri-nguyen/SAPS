import { describe, expect, it, vi } from "vitest";

import { ApiError } from "./client";
import { createSettingsApi } from "./settings";

const body = {
  priceToleranceUsd: "0.5000",
  approvalThresholdUsd: "300.00",
  updatedAt: "2026-12-01T08:00:00Z",
  updatedBy: "system",
};
const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });

describe("matching settings API client (SAPS-28)", () => {
  it("reads the settings with getMatchingSettings", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(json(body));
    expect(await createSettingsApi(fetchImpl).get()).toEqual(body);
    expect(fetchImpl).toHaveBeenCalledWith(
      "/v1/matching-settings",
      expect.objectContaining({ credentials: "same-origin" }),
    );
  });

  it("saves both values with updateMatchingSettings", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(json(body));
    const update = { priceToleranceUsd: "1.00", approvalThresholdUsd: "450" };
    expect(await createSettingsApi(fetchImpl).update(update)).toEqual(body);
    const [path, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/v1/matching-settings");
    expect(init.method).toBe("PUT");
    expect(JSON.parse(init.body as string)).toEqual(update);
    expect(new Headers(init.headers).get("Content-Type")).toBe("application/json");
  });

  it("throws the problem of a refused save", async () => {
    const problem = {
      type: "about:blank",
      title: "Unprocessable Content",
      status: 422,
      detail: "Not valid.",
    };
    const fetchImpl = vi.fn().mockResolvedValue(json(problem, 422));
    await expect(
      createSettingsApi(fetchImpl).update({ priceToleranceUsd: "-1", approvalThresholdUsd: "1" }),
    ).rejects.toBeInstanceOf(ApiError);
  });
});
