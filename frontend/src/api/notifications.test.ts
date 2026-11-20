import { describe, expect, it, vi } from "vitest";

import { ApiError } from "./client";
import { createNotificationApi } from "./notifications";

const json = (data: unknown, status = 200) =>
  new Response(JSON.stringify(data), { status, headers: { "Content-Type": "application/json" } });
const page = { items: [], nextPageToken: null, unreadCount: 3 };

describe("notification API client (SAPS-24)", () => {
  it("lists with the unread filter, page size and page token", async () => {
    const fetchImpl = vi.fn().mockImplementation(() => Promise.resolve(json(page))); // a body is read once
    const api = createNotificationApi(fetchImpl);
    expect(await api.list({ unreadOnly: true, pageSize: 1 })).toEqual(page);
    expect(fetchImpl.mock.calls[0]?.[0]).toBe("/v1/notifications?unreadOnly=true&pageSize=1");
    await api.list({ pageSize: 20, pageToken: "abc" });
    expect(fetchImpl.mock.calls[1]?.[0]).toBe("/v1/notifications?pageSize=20&pageToken=abc");
    await api.list();
    expect(fetchImpl.mock.calls[2]?.[0]).toBe("/v1/notifications?");
  });

  it("marks one notification read with POST", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    await createNotificationApi(fetchImpl).markRead("n 1");
    const [path, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect(path).toBe("/v1/notifications/n%201/read");
    expect(init.method).toBe("POST");
  });

  it("marks all notifications read with POST", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response(null, { status: 204 }));
    await createNotificationApi(fetchImpl).markAllRead();
    const [path, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect([path, init.method]).toEqual(["/v1/notifications/read-all", "POST"]);
  });

  it("throws the problem of a refused call", async () => {
    const problem = {
      type: "about:blank",
      title: "Not Found",
      status: 404,
      detail: "Notification not found.",
    };
    const fetchImpl = vi.fn().mockResolvedValue(json(problem, 404));
    await expect(createNotificationApi(fetchImpl).markRead("x")).rejects.toBeInstanceOf(ApiError);
  });
});
