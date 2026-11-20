import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { href, invoicePath, navigate, parseHash, useRoute } from "./routing";

describe("routing", () => {
  it.each([
    ["", { page: "" }],
    ["#/", { page: "" }],
    ["#/exceptions", { page: "exceptions" }],
    ["#exceptions", { page: "exceptions" }],
    ["#/invoices/inv%201", { page: "invoice", invoiceId: "inv 1" }],
    ["#/invoices/", { page: "invoices" }],
  ])("parses %s", (hash, route) => {
    expect(parseHash(hash)).toEqual(route);
  });

  it("builds links and paths", () => {
    expect(href("upload")).toBe("#/upload");
    expect(invoicePath("a/b")).toBe("invoices/a%2Fb");
  });

  it("follows hash changes", () => {
    const { result } = renderHook(() => useRoute());
    expect(result.current).toEqual({ page: "" });
    act(() => {
      navigate(invoicePath("inv-7"));
      window.dispatchEvent(new HashChangeEvent("hashchange"));
    });
    expect(window.location.hash).toBe("#/invoices/inv-7");
    expect(result.current).toEqual({ page: "invoice", invoiceId: "inv-7" });
  });
});
