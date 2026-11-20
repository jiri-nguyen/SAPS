import { ApiError, UNAUTHORIZED, apiFetch, type Problem, unauthorizedEvents } from "./client";
import type { components } from "./schema";

export type Invoice = components["schemas"]["Invoice"];
export type InvoiceStatus = components["schemas"]["InvoiceStatus"];

export interface InvoiceApi {
  /** `uploadInvoice`; `onProgress` gets the sent fraction 0…1. */
  upload(file: File, idempotencyKey: string, onProgress: (fraction: number) => void): Promise<Invoice>;
  /** `getInvoice`. */
  get(invoiceId: string): Promise<Invoice>;
}

function parseProblem(text: string): Problem | undefined {
  try {
    return JSON.parse(text) as Problem;
  } catch {
    return undefined;
  }
}

/**
 * Upload uses XMLHttpRequest because fetch reports no upload progress. Same origin: the browser sends the
 * session cookie and the Origin header (ADR-0008).
 */
export function createInvoiceApi(
  newRequest: () => XMLHttpRequest = () => new XMLHttpRequest(),
  fetchImpl: typeof fetch = fetch,
): InvoiceApi {
  return {
    upload(file, idempotencyKey, onProgress) {
      return new Promise((resolve, reject) => {
        const request = newRequest();
        request.open("POST", "/v1/invoices");
        request.setRequestHeader("Accept", "application/json");
        request.setRequestHeader("Idempotency-Key", idempotencyKey);
        request.upload.onprogress = (event) => {
          if (event.lengthComputable && event.total > 0) onProgress(event.loaded / event.total);
        };
        request.onload = () => {
          if (request.status >= 200 && request.status < 300) {
            onProgress(1);
            resolve(JSON.parse(request.responseText) as Invoice);
            return;
          }
          if (request.status === 401) unauthorizedEvents.dispatchEvent(new Event(UNAUTHORIZED));
          reject(new ApiError(request.status, parseProblem(request.responseText)));
        };
        request.onerror = () =>
          reject(new ApiError(0, { type: "about:blank", title: "Network error", status: 0 }));
        const body = new FormData();
        body.append("file", file);
        request.send(body);
      });
    },
    async get(invoiceId) {
      const response = await apiFetch(`/v1/invoices/${encodeURIComponent(invoiceId)}`, {}, fetchImpl);
      return (await response.json()) as Invoice;
    },
  };
}
