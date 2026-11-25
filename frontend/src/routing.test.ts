import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { detailPath, href, navigate, parseHash, useRoute } from "./routing";

describe("routing", () => {
  it.each([
    ["", { page: "" }],
    ["#/", { page: "" }],
    ["#/exceptions", { page: "exceptions" }],
    ["#exceptions", { page: "exceptions" }],
    ["#/exceptions/inv-1", { page: "exceptions", invoiceId: "inv-1" }],
    ["#/approvals/inv%201", { page: "approvals", invoiceId: "inv 1" }],
    ["#/invoices/inv-1", { page: "invoices", invoiceId: "inv-1" }], // an invoice opened from All invoices
    ["#/invoices/", { page: "invoices" }],
    [
      "#/invoices?vendor=alpha&status=COMPLETED",
      { page: "invoices", query: "vendor=alpha&status=COMPLETED" },
    ],
    ["#/invoices/inv-1?x=1", { page: "invoices", invoiceId: "inv-1", query: "x=1" }],
    ["#/exceptions?", { page: "exceptions" }],
    ["#/invoices?a=b?c", { page: "invoices", query: "a=b?c" }],
    ["#/upload/inv-1", { page: "upload" }],
  ])("parses %s", (hash, route) => {
    expect(parseHash(hash)).toEqual(route);
  });

  it("builds links and paths", () => {
    expect(href("upload")).toBe("#/upload");
    expect(detailPath("approvals", "a/b")).toBe("approvals/a%2Fb");
  });

  it("follows hash changes", () => {
    const { result } = renderHook(() => useRoute());
    expect(result.current).toEqual({ page: "" });
    act(() => {
      navigate(detailPath("exceptions", "inv-7"));
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(window.location.hash).toBe("#/exceptions/inv-7");
    expect(result.current).toEqual({ page: "exceptions", invoiceId: "inv-7" });
  });
});
