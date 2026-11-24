import { describe, expect, it, vi } from "vitest";

import { ApiError } from "./client";
import { createSessionApi } from "./session";

const USER = {
  id: "1",
  username: "member1",
  displayName: "Accounting Member 1",
  role: "ACCOUNTING_MEMBER",
  companyName: "Demo Vietnam",
};
const json = (status: number, body: unknown) =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("session API", () => {
  it("reads the current session", async () => {
    const api = createSessionApi(vi.fn().mockResolvedValue(json(200, USER)));
    expect(await api.getSession()).toEqual(USER);
  });

  it("returns null when not signed in", async () => {
    const api = createSessionApi(
      vi.fn().mockResolvedValue(json(401, { title: "Unauthorized", status: 401 })),
    );
    expect(await api.getSession()).toBeNull();
  });

  it("rethrows other errors", async () => {
    const api = createSessionApi(
      vi.fn().mockResolvedValue(json(500, { title: "Internal Server Error", status: 500 })),
    );
    await expect(api.getSession()).rejects.toBeInstanceOf(ApiError);
  });

  it("signs in with POST and signs out with DELETE", async () => {
    const fetchImpl = vi
      .fn()
      .mockResolvedValueOnce(json(200, USER))
      .mockResolvedValueOnce(new Response(null, { status: 204 }));
    const api = createSessionApi(fetchImpl);
    expect(await api.signIn("member1", "pw")).toEqual(USER);
    await api.signOut();
    const [path, signIn] = fetchImpl.mock.calls[0] as [string, RequestInit];
    const [, signOut] = fetchImpl.mock.calls[1] as [string, RequestInit];
    expect(path).toBe("/v1/session");
    expect(signIn.method).toBe("POST");
    expect(JSON.parse(signIn.body as string)).toEqual({ username: "member1", password: "pw" });
    expect(signOut.method).toBe("DELETE");
  });

  it("uses the global fetch by default", () => {
    expect(createSessionApi()).toHaveProperty("getSession");
  });
});
