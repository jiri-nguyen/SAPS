import { useEffect, useState } from "react";

/** A screen of the Web App, addressed by the URL hash: `#/exceptions`, `#/approvals/{id}`. */
export interface Route {
  page: string;
  invoiceId?: string;
  /** The query string after `?`, without it; the filters of `#/invoices?vendor=alpha` (SAPS-46). */
  query?: string;
}

/** Screens that open an invoice: `#/{screen}/{invoiceId}`; `invoices` is the list "All invoices" (SAPS-46). */
const DETAIL_QUEUES: ReadonlySet<string> = new Set(["exceptions", "approvals", "invoices"]);

export function parseHash(hash: string): Route {
  const [path = "", ...rest] = hash.replace(/^#\/?/, "").split("?");
  const query = rest.join("?");
  const [first = "", second] = path.split("/");
  const route: Route = { page: first };
  if (second && DETAIL_QUEUES.has(first)) route.invoiceId = decodeURIComponent(second);
  if (query) route.query = query;
  return route;
}

export function href(path: string): string {
  return `#/${path}`;
}

export function navigate(path: string): void {
  window.location.hash = href(path);
}

export function detailPath(queue: string, invoiceId: string): string {
  return `${queue}/${encodeURIComponent(invoiceId)}`;
}

/** The current route; follows browser Back / Forward and links. */
export function useRoute(): Route {
  const [route, setRoute] = useState(() => parseHash(window.location.hash));
  useEffect(() => {
    const onChange = () => setRoute(parseHash(window.location.hash));
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
  }, []);
  return route;
}
