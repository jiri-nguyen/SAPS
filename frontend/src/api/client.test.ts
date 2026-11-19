import { describe, expect, it, vi } from "vitest";

import { ApiError, UNAUTHORIZED, apiFetch, unauthorizedEvents } from "./client";

const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("apiFetch", () => {
  it("sends same-origin credentials and JSON headers", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(json(200, {}));
    await apiFetch("/v1/x", { method: "POST", body: "{}" }, fetchImpl);
    const [, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    const headers = init.headers as Headers;
    expect(init.credentials).toBe("same-origin");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("Accept")).toBe("application/json");
  });

  it("does not set a content type without a body", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(json(200, {}));
    await apiFetch("/v1/x", undefined, fetchImpl);
    const [, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect((init.headers as Headers).has("Content-Type")).toBe(false);
  });

  it("turns a problem answer into an ApiError", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(json(403, { type: "about:blank", title: "Forbidden", status: 403, detail: "No." }));
    const error = await apiFetch("/v1/x", {}, fetchImpl).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(403);
    expect((error as ApiError).message).toBe("No.");
  });

  it("copes with an error answer that is not JSON", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response("Bad gateway", { status: 502 }));
    const error = (await apiFetch("/v1/x", {}, fetchImpl).catch((e: unknown) => e)) as ApiError;
    expect(error.problem).toBeUndefined();
    expect(error.message).toBe("HTTP 502");
  });

  it("uses the problem title when there is no detail", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(json(404, { type: "about:blank", title: "Not Found", status: 404 }));
    const error = (await apiFetch("/v1/x", {}, fetchImpl).catch((e: unknown) => e)) as ApiError;
    expect(error.message).toBe("Not Found");
  });

  it("announces a 401", async () => {
    const listener = vi.fn();
    unauthorizedEvents.addEventListener(UNAUTHORIZED, listener);
    const fetchImpl = vi
      .fn()
      .mockResolvedValue(json(401, { type: "about:blank", title: "Unauthorized", status: 401 }));
    await expect(apiFetch("/v1/x", {}, fetchImpl)).rejects.toBeInstanceOf(ApiError);
    unauthorizedEvents.removeEventListener(UNAUTHORIZED, listener);
    expect(listener).toHaveBeenCalledOnce();
  });
});
