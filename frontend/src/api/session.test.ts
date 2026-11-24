import { describe, expect, it, vi } from "vitest";

import { ApiError } from "./client";
import { createSessionApi } from "./session";

const USER = {
  id: "1",
  username: "member1@vn.example.com",
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

  it("signs out with DELETE and returns the Identity Provider logout URL", async () => {
    const logoutUrl = "http://localhost:8080/realms/saps/protocol/openid-connect/logout?x=1";
    const fetchImpl = vi.fn().mockResolvedValueOnce(json(200, { logoutUrl }));
    const api = createSessionApi(fetchImpl);
    expect(await api.signOut()).toBe(logoutUrl);
    const [path, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/v1/session");
    expect(init.method).toBe("DELETE");
  });

  it("uses the global fetch by default", () => {
    expect(createSessionApi()).toHaveProperty("getSession");
  });
});
