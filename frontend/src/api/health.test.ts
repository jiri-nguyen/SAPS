import { describe, expect, it } from "vitest";

import { fetchApiHealth } from "./health";

const respond = (status: number, body: unknown) =>
  (() => Promise.resolve(new Response(JSON.stringify(body), { status }))) as typeof fetch;

describe("fetchApiHealth", () => {
  it("returns ok for a healthy API", async () => {
    expect(await fetchApiHealth(respond(200, { status: "ok" }))).toBe("ok");
  });

  it("returns unreachable for an error status", async () => {
    expect(await fetchApiHealth(respond(503, {}))).toBe("unreachable");
  });

  it("returns unreachable for an unexpected body", async () => {
    expect(await fetchApiHealth(respond(200, { status: "down" }))).toBe("unreachable");
  });

  it("returns unreachable when the request fails", async () => {
    const failing = (() => Promise.reject(new Error("network"))) as typeof fetch;
    expect(await fetchApiHealth(failing)).toBe("unreachable");
  });
});
