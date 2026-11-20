import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import type { ExceptionApi } from "../api/exceptions";
import {
  MANAGER,
  MEMBER,
  OTHER,
  claimedBy,
  fakeExceptionApi,
  invoiceFixture,
  versioned,
} from "../test/invoices";
import { InvoiceDetailPage } from "./InvoiceDetailPage";

const EVENTS = [
  {
    id: "e1",
    statusFrom: null,
    statusTo: "MATCHING" as const,
    action: "EXTRACT",
    actor: "system",
    details: null,
    occurredAt: "2026-12-15T09:00:00Z",
  },
  {
    id: "e2",
    statusFrom: "MATCHING" as const,
    statusTo: "EXCEPTION" as const,
    action: "MATCH",
    actor: "system",
    details: null,
    occurredAt: "2026-12-15T09:00:01Z",
  },
];

function problem(status: number, detail: string) {
  return new ApiError(status, { type: "about:blank", title: "x", status, detail });
}

function renderPage(api: ExceptionApi, user = MEMBER, pollMs = 10_000) {
  return render(<InvoiceDetailPage api={api} invoiceId="inv-12" user={user} pollMs={pollMs} />);
}

describe("InvoiceDetailPage", () => {
  it("shows the file, data, exceptions, lines and history", async () => {
    renderPage(fakeExceptionApi({ events: vi.fn().mockResolvedValue(EVENTS) }));
    expect(await screen.findByRole("heading", { name: /AOS-2026-1013/ })).toBeInTheDocument();
    expect(screen.getByTitle("Invoice file")).toHaveAttribute("src", "/v1/invoices/inv-12/file");
    expect(screen.getByText(/Unit price outside tolerance/)).toBeInTheDocument();
    const line = screen.getAllByRole("row")[1];
    expect(line).toHaveTextContent("0100012 / 1");
    expect(line).toHaveTextContent("20.60");
    expect(line).toHaveTextContent("mismatch");
    expect(screen.getByText(/EXTRACT · system · Matching/)).toBeInTheDocument();
    expect(screen.getByText("Claimed by nobody")).toBeInTheDocument();
  });

  it("shows an image file as an image", async () => {
    const image = invoiceFixture({
      file: { name: "scan.png", contentType: "image/png", sizeBytes: 1, sha256: "b".repeat(64) },
    });
    renderPage(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(image)) }));
    expect(await screen.findByRole("img", { name: "Invoice file" })).toHaveAttribute(
      "src",
      "/v1/invoices/inv-12/file",
    );
  });

  it("shows a load error", async () => {
    renderPage(
      fakeExceptionApi({ getVersioned: vi.fn().mockRejectedValue(problem(404, "Invoice not found.")) }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("Invoice not found.");
  });

  it("lets a member claim an unclaimed invoice", async () => {
    const getVersioned = vi
      .fn()
      .mockResolvedValueOnce(versioned(invoiceFixture()))
      .mockResolvedValue(versioned(claimedBy(MEMBER)));
    const api = fakeExceptionApi({ getVersioned });
    renderPage(api);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Claim" }));
    expect(await screen.findByText("You claimed this invoice.")).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Correct data" })).toBeInTheDocument();
    expect(api.claim).toHaveBeenCalledWith("inv-12");
  });

  it("shows no actions to a member who did not claim it", async () => {
    renderPage(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(claimedBy(OTHER))) }));
    expect(await screen.findByText("Claimed by Accounting Member 2")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Correct data" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Release claim" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Claim" })).not.toBeInTheDocument();
  });

  it("lets a manager only release a claim", async () => {
    const getVersioned = vi
      .fn()
      .mockResolvedValueOnce(versioned(claimedBy(OTHER)))
      .mockResolvedValue(versioned(invoiceFixture()));
    const api = fakeExceptionApi({ getVersioned });
    renderPage(api, MANAGER);
    expect(await screen.findByRole("button", { name: "Release claim" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Correct data" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Claim" })).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Release claim" }));
    expect(await screen.findByText("The claim was released.")).toBeInTheDocument();
    expect(api.release).toHaveBeenCalledWith("inv-12");
  });

  it("corrects the price, shows re-matching and polls until it ends", async () => {
    const update = vi
      .fn()
      .mockResolvedValue({ ...versioned(claimedBy(MEMBER, { status: "MATCHING" }), 'W/"2"'), rematch: true });
    const getVersioned = vi
      .fn()
      .mockResolvedValueOnce(versioned(claimedBy(MEMBER)))
      .mockResolvedValueOnce(versioned(claimedBy(MEMBER, { status: "MATCHING" }), 'W/"2"'))
      .mockResolvedValue(versioned(invoiceFixture({ status: "PENDING_REVIEW", exceptions: [] }), 'W/"3"'));
    renderPage(fakeExceptionApi({ getVersioned, update }), MEMBER, 20);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Correct data" }));
    const price = screen.getByRole("textbox", { name: "Unit price, row 1" });
    await user.clear(price);
    await user.type(price, "20.00");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(update).toHaveBeenCalledWith(
      "inv-12",
      { lines: [expect.objectContaining({ lineNumber: 1, unitPrice: "20.00", quantity: "4" })] },
      'W/"1"',
    );
    expect(
      await screen.findByText("Saved. Matching runs again with the corrected data."),
    ).toBeInTheDocument();
    expect(await screen.findByText(/exception handling is finished/)).toBeInTheDocument();
    expect(screen.getByText("Pending review", { selector: ".badge" })).toBeInTheDocument();
    await waitFor(() => expect(getVersioned.mock.calls.length).toBeGreaterThanOrEqual(3));
  });

  it("saves other fields without re-matching, and edits lines", async () => {
    const update = vi.fn().mockResolvedValue({ ...versioned(claimedBy(MEMBER)), rematch: false });
    renderPage(
      fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(claimedBy(MEMBER))), update }),
    );
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Correct data" }));
    const name = screen.getByRole("textbox", { name: "Vendor name" });
    await user.clear(name);
    await user.type(name, "Alpha Ltd.");
    await user.click(screen.getByRole("button", { name: "Add line" }));
    expect(screen.getByRole("textbox", { name: "Line, row 2" })).toHaveValue("2");
    await user.click(screen.getAllByRole("button", { name: "Remove" })[1] as HTMLElement);
    expect(screen.getByRole("button", { name: "Remove" })).toBeDisabled(); // at least one line stays
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(update).toHaveBeenCalledWith("inv-12", { vendorName: "Alpha Ltd." }, 'W/"1"');
    expect(await screen.findByText("Saved.")).toBeInTheDocument();
  });

  it("checks the form before saving", async () => {
    const update = vi.fn();
    renderPage(
      fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(claimedBy(MEMBER))), update }),
    );
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Correct data" }));
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Nothing changed.");
    const po = screen.getByRole("textbox", { name: "PO number, row 1" });
    await user.clear(po);
    await user.type(po, "123");
    await user.click(screen.getByRole("button", { name: "Save" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Line 1: the PO number has 7 digits.");
    expect(update).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("form", { name: "Correct invoice data" })).not.toBeInTheDocument();
  });

  it("enters the data of an unreadable invoice from an empty line", async () => {
    const unreadable = claimedBy(MEMBER, { lines: [], vendorCode: null, exceptions: [] });
    renderPage(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(unreadable)) }));
    await userEvent.setup().click(await screen.findByRole("button", { name: "Correct data" }));
    expect(screen.getByRole("textbox", { name: "Line, row 1" })).toHaveValue("1");
  });

  it("accepts acceptable exceptions as is and names the next step", async () => {
    const resolve = vi.fn().mockResolvedValue(versioned(invoiceFixture({ status: "PENDING_APPROVAL" })));
    renderPage(
      fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(claimedBy(MEMBER))), resolve }),
    );
    await userEvent.setup().click(await screen.findByRole("button", { name: "Accept as is" }));
    expect(resolve).toHaveBeenCalledWith("inv-12", 'W/"1"');
    expect(await screen.findByText("Accepted. Next step: Pending approval.")).toBeInTheDocument();
  });

  it("explains why some exceptions cannot be accepted as is", async () => {
    const invoice = claimedBy(MEMBER, {
      exceptions: [
        { ...invoiceFixture().exceptions[0], id: "ex-3", code: "EX3", message: "Invalid PO" } as never,
      ],
    });
    renderPage(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(invoice)) }));
    expect(await screen.findByRole("button", { name: "Accept as is" })).toBeDisabled();
    expect(
      screen.getByText("EX3 cannot be accepted as is: correct the data or reject the invoice."),
    ).toBeInTheDocument();
  });

  it("rejects with a reason", async () => {
    const reject = vi.fn().mockResolvedValue(versioned(invoiceFixture({ status: "REJECTED" })));
    renderPage(
      fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(claimedBy(MEMBER))), reject }),
    );
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Reject" }));
    await user.click(screen.getByRole("button", { name: "Reject invoice" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter the reason for the rejection.");
    await user.type(screen.getByRole("textbox", { name: "Reason" }), "  PO does not exist. ");
    await user.click(screen.getByRole("button", { name: "Reject invoice" }));
    expect(reject).toHaveBeenCalledWith("inv-12", "PO does not exist.");
    expect(await screen.findByText("The invoice was rejected.")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Reject" }));
    await user.click(screen.getByRole("button", { name: "Cancel" }));
    expect(screen.queryByRole("form", { name: "Reject invoice" })).not.toBeInTheDocument();
  });

  it("reloads after a stale ETag and shows other problems", async () => {
    const resolve = vi
      .fn()
      .mockRejectedValueOnce(problem(412, "The invoice changed since you loaded it."))
      .mockRejectedValueOnce(problem(409, "Re-matching is in progress."));
    const getVersioned = vi.fn().mockResolvedValue(versioned(claimedBy(MEMBER)));
    renderPage(fakeExceptionApi({ getVersioned, resolve }));
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Accept as is" }));
    expect(await screen.findByText(/It has been reloaded/)).toBeInTheDocument();
    await waitFor(() => expect(getVersioned).toHaveBeenCalledTimes(2));
    await user.click(screen.getByRole("button", { name: "Accept as is" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Re-matching is in progress.");
  });

  it("shows resolved exceptions and who resolved them", async () => {
    const invoice = invoiceFixture({
      status: "PENDING_REVIEW",
      exceptions: [
        {
          ...invoiceFixture().exceptions[0],
          status: "RESOLVED",
          resolvedBy: { id: "u", displayName: "Accounting Member 1" },
        } as never,
        {
          ...invoiceFixture().exceptions[0],
          id: "ex-9",
          code: "EX9",
          status: "RESOLVED",
          resolvedBy: null,
        } as never,
      ],
    });
    renderPage(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(invoice)) }));
    expect(await screen.findByText(/resolved by Accounting Member 1/)).toBeInTheDocument();
    expect(within(document.body).getByText(/Duplicate invoice/).parentElement).toHaveTextContent(
      "(resolved)",
    );
    expect(screen.queryByRole("group", { name: "Actions" })).not.toBeInTheDocument();
  });

  it("stops polling when leaving the page", async () => {
    const getVersioned = vi.fn().mockResolvedValue(versioned(claimedBy(MEMBER, { status: "MATCHING" })));
    const { unmount } = renderPage(fakeExceptionApi({ getVersioned }), MEMBER, 5);
    expect(await screen.findByText("Re-matching in progress…")).toBeInTheDocument();
    unmount();
    const calls = getVersioned.mock.calls.length;
    await act(() => new Promise((resolve) => setTimeout(resolve, 30)));
    expect(getVersioned).toHaveBeenCalledTimes(calls);
  });
});
