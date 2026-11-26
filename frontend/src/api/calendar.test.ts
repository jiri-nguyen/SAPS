import { describe, expect, it, vi } from "vitest";

import { ApiError } from "./client";
import { createCalendarApi } from "./calendar";

const CALENDAR = { rules: [], timeZone: "Asia/Singapore", closedToday: false, openAgainOn: null };

describe("calendar API", () => {
  it("reads the calendar", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response(JSON.stringify(CALENDAR), { status: 200 }));
    await expect(createCalendarApi(fetchImpl).get()).resolves.toEqual(CALENDAR);
    expect(fetchImpl.mock.calls[0]?.[0]).toBe("/v1/processing-calendar");
  });

  it("replaces all rules with PUT", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response(JSON.stringify(CALENDAR), { status: 200 }));
    const rules = [{ kind: "WEEKDAY" as const, weekday: 6 }];
    await createCalendarApi(fetchImpl).replace(rules);
    const [url, init] = fetchImpl.mock.calls[0] as [string, RequestInit];
    expect([url, init.method]).toEqual(["/v1/processing-calendar", "PUT"]);
    expect(JSON.parse(init.body as string)).toEqual({ rules });
  });

  it("raises the problem of a refused calendar", async () => {
    const problem = { type: "about:blank", title: "x", status: 422, errors: [{ field: "rules[0].weekday" }] };
    const fetchImpl = vi.fn().mockResolvedValue(new Response(JSON.stringify(problem), { status: 422 }));
    await expect(createCalendarApi(fetchImpl).replace([])).rejects.toBeInstanceOf(ApiError);
  });

  it("uses the global fetch by default", () => {
    expect(createCalendarApi()).toHaveProperty("get");
  });
});
