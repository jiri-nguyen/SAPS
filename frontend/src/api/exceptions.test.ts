import { describe, expect, it, vi } from "vitest";

import { ApiError } from "./client";
import { createExceptionApi } from "./exceptions";

const INVOICE = { id: "inv-1", status: "EXCEPTION" };

function reply(status: number, body: unknown, headers: Record<string, string> = {}) {
  return new Response(body === null ? null : JSON.stringify(body), { status, headers });
}

function setup(...responses: Response[]) {
  const fetchImpl = vi.fn();
  for (const response of responses) fetchImpl.mockResolvedValueOnce(response);
  return { fetchImpl, api: createExceptionApi(fetchImpl) };
}

const call = (fetchImpl: ReturnType<typeof vi.fn>, index = 0) => {
  const [url, init] = fetchImpl.mock.calls[index] as [string, RequestInit];
  return { url, init, headers: init.headers as Headers };
};

describe("exception API", () => {
  it("reads an invoice with its ETag", async () => {
    const { api, fetchImpl } = setup(reply(200, INVOICE, { ETag: 'W/"5"' }));
    await expect(api.getVersioned("inv 1")).resolves.toEqual({ invoice: INVOICE, etag: 'W/"5"' });
    expect(call(fetchImpl).url).toBe("/v1/invoices/inv%201");
  });

  it("lists with repeated status and the other filters", async () => {
    const page = { items: [], nextPageToken: null };
    const { api, fetchImpl } = setup(reply(200, page), reply(200, page));
    await api.list({ status: ["EXCEPTION", "MATCHING"], assignee: "me", pageToken: "t1", pageSize: 5 });
    expect(call(fetchImpl).url).toBe(
      "/v1/invoices?status=EXCEPTION&status=MATCHING&assignee=me&pageToken=t1&pageSize=5",
    );
    await api.list({});
    expect(call(fetchImpl, 1).url).toBe("/v1/invoices?");
  });

  it("claims and releases", async () => {
    const { api, fetchImpl } = setup(reply(200, INVOICE), reply(204, null));
    await expect(api.claim("inv-1")).resolves.toEqual({ invoice: INVOICE, etag: "" });
    await api.release("inv-1");
    expect([call(fetchImpl).init.method, call(fetchImpl).url]).toEqual(["POST", "/v1/invoices/inv-1/claim"]);
    expect([call(fetchImpl, 1).init.method, call(fetchImpl, 1).url]).toEqual([
      "DELETE",
      "/v1/invoices/inv-1/claim",
    ]);
  });

  it("updates with If-Match and tells a re-match (202) from a plain save (200)", async () => {
    const { api, fetchImpl } = setup(
      reply(202, INVOICE, { ETag: 'W/"6"' }),
      reply(200, INVOICE, { ETag: 'W/"7"' }),
    );
    await expect(api.update("inv-1", { vendorName: "X" }, 'W/"5"')).resolves.toMatchObject({
      rematch: true,
      etag: 'W/"6"',
    });
    await expect(api.update("inv-1", { vendorName: "Y" }, 'W/"6"')).resolves.toMatchObject({
      rematch: false,
    });
    const first = call(fetchImpl);
    expect(first.init.method).toBe("PATCH");
    expect(first.headers.get("If-Match")).toBe('W/"5"');
    expect(first.headers.get("Content-Type")).toBe("application/json");
    expect(JSON.parse(first.init.body as string)).toEqual({ vendorName: "X" });
  });

  it("resolves with If-Match and rejects with a reason", async () => {
    const { api, fetchImpl } = setup(reply(200, INVOICE), reply(200, INVOICE));
    await api.resolve("inv-1", 'W/"8"');
    await api.reject("inv-1", "Not ours.");
    expect(call(fetchImpl).url).toBe("/v1/invoices/inv-1/resolution");
    expect(call(fetchImpl).headers.get("If-Match")).toBe('W/"8"');
    expect(call(fetchImpl, 1).url).toBe("/v1/invoices/inv-1/rejection");
    expect(JSON.parse(call(fetchImpl, 1).init.body as string)).toEqual({ reason: "Not ours." });
  });

  it("confirms the final result (SAPS-21)", async () => {
    const { api, fetchImpl } = setup(reply(200, INVOICE, { ETag: 'W/"9"' }));
    await expect(api.confirm("inv-1")).resolves.toEqual({ invoice: INVOICE, etag: 'W/"9"' });
    expect([call(fetchImpl).init.method, call(fetchImpl).url]).toEqual([
      "POST",
      "/v1/invoices/inv-1/confirmation",
    ]);
  });

  it("decides an approval with and without a comment (SAPS-22)", async () => {
    const { api, fetchImpl } = setup(reply(200, INVOICE), reply(200, INVOICE));
    await api.decide("inv-1", "APPROVED");
    await api.decide("inv-1", "REJECTED", "Price is not agreed.");
    expect(call(fetchImpl).url).toBe("/v1/invoices/inv-1/approval");
    expect(call(fetchImpl).init.method).toBe("POST");
    expect(JSON.parse(call(fetchImpl).init.body as string)).toEqual({ decision: "APPROVED" });
    expect(JSON.parse(call(fetchImpl, 1).init.body as string)).toEqual({
      decision: "REJECTED",
      comment: "Price is not agreed.",
    });
  });

  it("reads every page of the history", async () => {
    const { api, fetchImpl } = setup(
      reply(200, { items: [{ id: "e1" }], nextPageToken: "n1" }),
      reply(200, { items: [{ id: "e2" }], nextPageToken: null }),
    );
    await expect(api.events("inv-1")).resolves.toEqual([{ id: "e1" }, { id: "e2" }]);
    expect(call(fetchImpl).url).toBe("/v1/invoices/inv-1/events?pageSize=100");
    expect(call(fetchImpl, 1).url).toBe("/v1/invoices/inv-1/events?pageSize=100&pageToken=n1");
  });

  it("passes problems on and builds the file URL", async () => {
    const { api } = setup(
      reply(409, { title: "Conflict", status: 409, detail: "Re-matching is in progress." }),
    );
    await expect(api.claim("inv-1")).rejects.toEqual(expect.objectContaining({ status: 409 }));
    expect(api.fileUrl("inv 1")).toBe("/v1/invoices/inv%201/file");
    expect(new ApiError(412).status).toBe(412);
    expect(createExceptionApi()).toHaveProperty("list");
  });
});
