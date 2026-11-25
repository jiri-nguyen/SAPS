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

/** The filters of the screen "All invoices" (SAPS-46); every one is optional and the names are the API's. */
export interface SearchFilters {
  status?: InvoiceStatus[];
  vendor?: string;
  invoiceNumber?: string;
  poNumber?: string;
  invoiceDateFrom?: string;
  invoiceDateTo?: string;
  uploadedFrom?: string;
  uploadedTo?: string;
  totalMin?: string;
  totalMax?: string;
  channel?: "UPLOAD" | "MAIL";
}

export interface ListQuery extends SearchFilters {
  assignee?: "me" | "unassigned";
  pageToken?: string;
  pageSize?: number;
}

const TEXT_FILTERS = [
  "vendor",
  "invoiceNumber",
  "poNumber",
  "invoiceDateFrom",
  "invoiceDateTo",
  "uploadedFrom",
  "uploadedTo",
  "totalMin",
  "totalMax",
  "channel",
] as const;

/** The filters as query parameters, in the order of the screen; empty values are left out. */
export function filterParams(filters: SearchFilters): URLSearchParams {
  const params = new URLSearchParams();
  for (const status of filters.status ?? []) params.append("status", status);
  for (const name of TEXT_FILTERS) {
    const value = filters[name]?.trim();
    if (value) params.set(name, value);
  }
  return params;
}

/** The filters in a query string (`vendor=alpha&status=COMPLETED`); unknown names are ignored. */
export function parseFilters(query: string): SearchFilters {
  const params = new URLSearchParams(query);
  const filters: SearchFilters = {};
  const status = params.getAll("status") as InvoiceStatus[];
  if (status.length > 0) filters.status = status;
  for (const name of TEXT_FILTERS) {
    const value = params.get(name);
    if (value) (filters as Record<string, string>)[name] = value;
  }
  return filters;
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
  /** `confirmInvoice` (SAPS-21): Pending review → Completed. */
  confirm(invoiceId: string): Promise<Versioned>;
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
      const params = filterParams(query);
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
    async confirm(invoiceId) {
      return versioned(await call(path(invoiceId, "/confirmation"), { method: "POST" }));
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
