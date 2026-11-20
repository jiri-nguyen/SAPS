import { describe, expect, it, vi } from "vitest";

import { ApiError, UNAUTHORIZED, unauthorizedEvents } from "./client";
import { createInvoiceApi } from "./invoices";

const INVOICE = { id: "inv-1", status: "UPLOADED" };

/** Minimal XMLHttpRequest double: records the request and lets the test answer it. */
class FakeRequest {
  method = "";
  url = "";
  headers: Record<string, string> = {};
  body: unknown;
  status = 0;
  responseText = "";
  upload: { onprogress: ((event: ProgressEvent) => void) | null } = { onprogress: null };
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;

  open(method: string, url: string) {
    this.method = method;
    this.url = url;
  }
  setRequestHeader(name: string, value: string) {
    this.headers[name] = value;
  }
  send(body: unknown) {
    this.body = body;
  }
  answer(status: number, body: string) {
    this.status = status;
    this.responseText = body;
    this.onload?.();
  }
}

function setup() {
  const request = new FakeRequest();
  const api = createInvoiceApi(() => request as unknown as XMLHttpRequest);
  return { request, api };
}

describe("invoice API", () => {
  it("uploads the file with its Idempotency-Key and reports progress", async () => {
    const { request, api } = setup();
    const progress: number[] = [];
    const file = new File(["%PDF-1.7"], "a.pdf", { type: "application/pdf" });
    const result = api.upload(file, "key-1", (p) => progress.push(p));
    expect(request.method).toBe("POST");
    expect(request.url).toBe("/v1/invoices");
    expect(request.headers["Idempotency-Key"]).toBe("key-1");
    expect((request.body as FormData).get("file")).toBe(file);
    request.upload.onprogress?.({ lengthComputable: true, loaded: 5, total: 10 } as ProgressEvent);
    request.upload.onprogress?.({ lengthComputable: false, loaded: 1, total: 0 } as ProgressEvent);
    request.answer(202, JSON.stringify(INVOICE));
    await expect(result).resolves.toEqual(INVOICE);
    expect(progress).toEqual([0.5, 1]);
  });

  it("turns a problem answer into an ApiError", async () => {
    const { request, api } = setup();
    const result = api.upload(new File(["x"], "x.pdf"), "k", () => {});
    request.answer(
      415,
      JSON.stringify({
        title: "Unsupported Media Type",
        status: 415,
        detail: "Only PDF, JPEG and PNG files are accepted.",
      }),
    );
    await expect(result).rejects.toMatchObject({
      status: 415,
      message: "Only PDF, JPEG and PNG files are accepted.",
    });
  });

  it("announces a 401 and copes with a body that is not JSON", async () => {
    const { request, api } = setup();
    const listener = vi.fn();
    unauthorizedEvents.addEventListener(UNAUTHORIZED, listener);
    const result = api.upload(new File(["x"], "x.pdf"), "k", () => {});
    request.answer(401, "not json");
    await expect(result).rejects.toBeInstanceOf(ApiError);
    unauthorizedEvents.removeEventListener(UNAUTHORIZED, listener);
    expect(listener).toHaveBeenCalledOnce();
  });

  it("reports a network error as status 0", async () => {
    const { request, api } = setup();
    const result = api.upload(new File(["x"], "x.pdf"), "k", () => {});
    request.onerror?.();
    await expect(result).rejects.toMatchObject({ status: 0 });
  });

  it("reads an invoice with getInvoice", async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response(JSON.stringify(INVOICE), { status: 200 }));
    const api = createInvoiceApi(undefined, fetchImpl);
    await expect(api.get("inv 1")).resolves.toEqual(INVOICE);
    expect(fetchImpl.mock.calls[0]?.[0]).toBe("/v1/invoices/inv%201");
  });

  it("uses the browser request by default", () => {
    expect(createInvoiceApi()).toHaveProperty("upload");
  });
});
