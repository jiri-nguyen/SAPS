import { useEffect, useState } from "react";

/** A screen of the Web App, addressed by the URL hash: `#/exceptions`, `#/approvals/{id}`. */
export interface Route {
  page: string;
  invoiceId?: string;
}

/** Queues that open an invoice: `#/{queue}/{invoiceId}` (`#/invoices/{id}` is the old link to the exception queue). */
const DETAIL_QUEUES: ReadonlySet<string> = new Set(["exceptions", "approvals", "review"]);

export function parseHash(hash: string): Route {
  const [first = "", second] = hash.replace(/^#\/?/, "").split("/");
  if (second && DETAIL_QUEUES.has(first)) return { page: first, invoiceId: decodeURIComponent(second) };
  if (second && first === "invoices") return { page: "exceptions", invoiceId: decodeURIComponent(second) };
  return { page: first };
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
