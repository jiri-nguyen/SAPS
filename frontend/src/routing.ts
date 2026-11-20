import { useEffect, useState } from "react";

/** A screen of the Web App, addressed by the URL hash: `#/exceptions`, `#/invoices/{id}`. */
export interface Route {
  page: string;
  invoiceId?: string;
}

export function parseHash(hash: string): Route {
  const [first = "", second] = hash.replace(/^#\/?/, "").split("/");
  if (first === "invoices" && second) return { page: "invoice", invoiceId: decodeURIComponent(second) };
  return { page: first };
}

export function href(path: string): string {
  return `#/${path}`;
}

export function navigate(path: string): void {
  window.location.hash = href(path);
}

export function invoicePath(invoiceId: string): string {
  return `invoices/${encodeURIComponent(invoiceId)}`;
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
