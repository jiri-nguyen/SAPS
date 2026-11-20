import { apiFetch } from "./client";
import type { Invoice, InvoiceStatus } from "./invoices";
import type { components } from "./schema";

export type InvoiceSummary = components["schemas"]["InvoiceSummary"];
export type InvoiceSummaryPage = components["schemas"]["InvoiceSummaryPage"];
export type InvoiceEvent = components["schemas"]["InvoiceEvent"];
export type InvoiceUpdate = components["schemas"]["InvoiceUpdate"];
export type InvoiceLineUpdate = components["schemas"]["InvoiceLineUpdate"];

/** An invoice with its version; send the ETag back as If-Match (SAPS-20 EC-02). */
export interface Versioned {
  invoice: Invoice;
  etag: string;
}

export interface UpdateResult extends Versioned {
  /** True when a matching field changed and re-matching is queued (202). */
  rematch: boolean;
}

export interface ListQuery {
  status?: InvoiceStatus[];
  assignee?: "me" | "unassigned";
  pageToken?: string;
  pageSize?: number;
}

/** Exception handling operations of the SAPS API (SAPS-20). */
export interface ExceptionApi {
  getVersioned(invoiceId: string): Promise<Versioned>;
  list(query: ListQuery): Promise<InvoiceSummaryPage>;
  claim(invoiceId: string): Promise<Versioned>;
  release(invoiceId: string): Promise<void>;
  update(invoiceId: string, body: InvoiceUpdate, etag: string): Promise<UpdateResult>;
  resolve(invoiceId: string, etag: string): Promise<Versioned>;
  reject(invoiceId: string, reason: string): Promise<Versioned>;
  /** `decideInvoiceApproval` (SAPS-22): a comment is required when rejecting. */
  decide(invoiceId: string, decision: "APPROVED" | "REJECTED", comment?: string): Promise<Versioned>;
  /** The whole audit trail, oldest first. */
  events(invoiceId: string): Promise<InvoiceEvent[]>;
  /** `downloadInvoiceFile`, for an iframe or image on the same origin. */
  fileUrl(invoiceId: string): string;
}

const path = (invoiceId: string, rest = "") => `/v1/invoices/${encodeURIComponent(invoiceId)}${rest}`;

async function versioned(response: Response): Promise<Versioned> {
  return { invoice: (await response.json()) as Invoice, etag: response.headers.get("ETag") ?? "" };
}

export function createExceptionApi(fetchImpl: typeof fetch = fetch): ExceptionApi {
  const call = (url: string, init: RequestInit = {}) => apiFetch(url, init, fetchImpl);
  return {
    async getVersioned(invoiceId) {
      return versioned(await call(path(invoiceId)));
    },
    async list(query) {
      const params = new URLSearchParams();
      for (const status of query.status ?? []) params.append("status", status);
      if (query.assignee) params.set("assignee", query.assignee);
      if (query.pageToken) params.set("pageToken", query.pageToken);
      if (query.pageSize) params.set("pageSize", String(query.pageSize));
      const response = await call(`/v1/invoices?${params.toString()}`);
      return (await response.json()) as InvoiceSummaryPage;
    },
    async claim(invoiceId) {
      return versioned(await call(path(invoiceId, "/claim"), { method: "POST" }));
    },
    async release(invoiceId) {
      await call(path(invoiceId, "/claim"), { method: "DELETE" });
    },
    async update(invoiceId, body, etag) {
      const response = await call(path(invoiceId), {
        method: "PATCH",
        body: JSON.stringify(body),
        headers: { "If-Match": etag },
      });
      return { ...(await versioned(response)), rematch: response.status === 202 };
    },
    async resolve(invoiceId, etag) {
      return versioned(
        await call(path(invoiceId, "/resolution"), { method: "POST", headers: { "If-Match": etag } }),
      );
    },
    async reject(invoiceId, reason) {
      return versioned(
        await call(path(invoiceId, "/rejection"), { method: "POST", body: JSON.stringify({ reason }) }),
      );
    },
    async decide(invoiceId, decision, comment) {
      const body: components["schemas"]["ApprovalCreate"] = comment ? { decision, comment } : { decision };
      return versioned(
        await call(path(invoiceId, "/approval"), { method: "POST", body: JSON.stringify(body) }),
      );
    },
    async events(invoiceId) {
      const items: InvoiceEvent[] = [];
      let token: string | null | undefined;
      do {
        const query = new URLSearchParams({ pageSize: "100", ...(token ? { pageToken: token } : {}) });
        const page = (await (
          await call(path(invoiceId, `/events?${query.toString()}`))
        ).json()) as components["schemas"]["InvoiceEventPage"];
        items.push(...page.items);
        token = page.nextPageToken;
      } while (token);
      return items;
    },
    fileUrl(invoiceId) {
      return path(invoiceId, "/file");
    },
  };
}
