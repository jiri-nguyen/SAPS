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

  it("shows the DO number, the matched lot and the PIR price of a trade PO line (SAPS-51)", async () => {
    const [base] = invoiceFixture().lines;
    if (!base) throw new Error("fixture has a line");
    const withLot = invoiceFixture({
      lines: [
        {
          ...base,
          doNumber: null,
          matchedDoNumber: "DO-7000021B",
          pirUnitPrice: "40.0000",
          poUnitPrice: "38.0000",
          unitPrice: "40.0000",
        },
        {
          ...base,
          id: "line-2",
          lineNumber: 2,
          doNumber: "DO-7000021A",
          matchedDoNumber: "DO-7000021A",
          pirUnitPrice: null,
          poUnitPrice: "15.0000",
        },
      ],
    });
    renderPage(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(withLot)) }));
    await screen.findByRole("heading", { name: /AOS-2026-1013/ });
    expect(screen.getByRole("columnheader", { name: "DO number" })).toBeInTheDocument();
    expect(screen.getByRole("columnheader", { name: "Reference price" })).toBeInTheDocument();
    const rows = screen.getAllByRole("row");
    const first = rows[1] as HTMLElement;
    const second = rows[2] as HTMLElement;
    expect(first).toHaveTextContent("→ lot DO-7000021B"); // no DO on the invoice: the only lot was used
    expect(first.querySelector("td[title]")).toHaveAttribute("title", "Purchasing info record");
    expect(first).toHaveTextContent("40.00");
    expect(second).toHaveTextContent("DO-7000021A");
    expect(second).not.toHaveTextContent("→ lot");
    expect(second.querySelector("td[title]")).toHaveAttribute("title", "PO unit price");
  });

  it("names the new exception types (DEC-068)", async () => {
    const [template] = invoiceFixture().exceptions;
    if (!template) throw new Error("fixture has an exception");
    const open = (code: "EX11" | "EX12" | "EX13", message: string) => ({
      ...template,
      id: code,
      code,
      message,
    });
    const invoice = invoiceFixture({
      exceptions: [
        open("EX11", "Line 1: DO number required."),
        open("EX12", "Line 1: no PIR."),
        open("EX13", "Line 1: DO-X unknown."),
      ],
    });
    renderPage(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(invoice)) }));
    await screen.findByRole("heading", { name: /AOS-2026-1013/ });
    expect(screen.getByText(/DO number missing: Line 1: DO number required/)).toBeInTheDocument();
    expect(screen.getByText(/No purchasing info record: Line 1: no PIR/)).toBeInTheDocument();
    expect(screen.getByText(/Invalid DO number: Line 1: DO-X unknown/)).toBeInTheDocument();
  });

  it("shows where an invoice received by mail came from, and nothing for an upload (SAPS-45)", async () => {
    const mail = invoiceFixture({
      uploadedBy: null,
      source: {
        channel: "MAIL",
        mailFrom: "Vendor Ltd <billing@vendor.example.net>",
        mailSubject: "March invoice",
        mailReceivedAt: "2027-03-01T02:30:00Z",
      },
    });
    const { unmount } = renderPage(
      fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(mail)) }),
    );
    expect(await screen.findByTestId("mail-source")).toHaveTextContent(
      "Received by mail from Vendor Ltd <billing@vendor.example.net> · March invoice · 2027-03-01 02:30 UTC",
    );
    unmount();
    renderPage(fakeExceptionApi());
    await screen.findByText("ds-12.pdf");
    expect(screen.queryByTestId("mail-source")).not.toBeInTheDocument();
  });

  it("lets an Accounting Manager process a held invoice now (SAPS-52 BR-06, BR-09)", async () => {
    const held = invoiceFixture({ status: "ON_HOLD", exceptions: [], lines: [], assignedTo: null });
    const released = invoiceFixture({ status: "UPLOADED", exceptions: [], lines: [] });
    const releaseHold = vi.fn().mockResolvedValue(versioned(released));
    renderPage(
      fakeExceptionApi({
        getVersioned: vi.fn().mockResolvedValueOnce(versioned(held)).mockResolvedValue(versioned(released)),
        releaseHold,
      }),
      MANAGER,
    );
    expect(await screen.findByText(/received in a closed period and is on hold/)).toHaveTextContent(
      "Process now",
    );
    expect(screen.getByText("On hold")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Claim" })).not.toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Process now" }));
    expect(releaseHold).toHaveBeenCalledWith("inv-12");
    expect(await screen.findByText("Released. The invoice is processed now.")).toBeInTheDocument();
  });

  it("tells a member that a held invoice waits for the end of the period, with no action", async () => {
    const held = invoiceFixture({ status: "ON_HOLD", exceptions: [], lines: [], assignedTo: null });
    renderPage(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(held)) }), MEMBER);
    expect(
      await screen.findByText(
        "This invoice was received in a closed period and is on hold. It is processed when the period ends.",
      ),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Process now" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Claim" })).not.toBeInTheDocument();
  });

  it("shows a refused Process now, for example an invoice that was released meanwhile", async () => {
    const held = invoiceFixture({ status: "ON_HOLD", exceptions: [], lines: [] });
    const releaseHold = vi.fn().mockRejectedValue(problem(409, "The invoice is not on hold."));
    renderPage(
      fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(held)), releaseHold }),
      MANAGER,
    );
    await userEvent.setup().click(await screen.findByRole("button", { name: "Process now" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The invoice is not on hold.");
  });

  it("shows the ERP document of a posted invoice and the earlier states (SAPS-49)", async () => {
    const posted = invoiceFixture({
      status: "POSTED",
      erpDocumentNumber: "MOCK-0A1B2C3D4E",
      postedAt: "2027-03-05T10:00:00Z",
      exceptions: [],
    });
    const { unmount } = renderPage(
      fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(posted)) }),
    );
    expect(
      await screen.findByText("Posted to the ERP: document MOCK-0A1B2C3D4E on 2027-03-05 10:00 UTC."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept as is" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Reject" })).not.toBeInTheDocument(); // BR-07
    unmount();
    const old = invoiceFixture({ status: "PENDING_REVIEW", exceptions: [] });
    renderPage(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(old)) }));
    expect(await screen.findByText(/state of an earlier version/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm" })).not.toBeInTheDocument(); // no final review
  });

  it("polls an invoice in Posting until it is posted (SAPS-49)", async () => {
    const posting = invoiceFixture({ status: "POSTING", exceptions: [] });
    const posted = invoiceFixture({
      status: "POSTED",
      erpDocumentNumber: "MOCK-0A1B2C3D4E",
      postedAt: "2027-03-05T10:00:00Z",
      exceptions: [],
    });
    const getVersioned = vi
      .fn()
      .mockResolvedValueOnce(versioned(posting))
      .mockResolvedValue(versioned(posted, 'W/"2"'));
    renderPage(fakeExceptionApi({ getVersioned }), MEMBER, 20);
    expect(await screen.findByText(/waiting to be posted to the ERP/)).toBeInTheDocument();
    expect(await screen.findByText(/Posted to the ERP: document MOCK-0A1B2C3D4E/)).toBeInTheDocument();
    await waitFor(() => expect(getVersioned.mock.calls.length).toBeGreaterThanOrEqual(2));
    const calls = getVersioned.mock.calls.length;
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(getVersioned.mock.calls.length).toBe(calls); // polling stops once it is Posted
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
      .mockResolvedValue(versioned(invoiceFixture({ status: "POSTING", exceptions: [] }), 'W/"3"'));
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
    expect(await screen.findByText(/waiting to be posted to the ERP/)).toBeInTheDocument(); // SAPS-49
    expect(screen.getByText("Posting", { selector: ".badge" })).toBeInTheDocument();
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

  it("accepts acceptable exceptions as is, then matching runs again (SAPS-49 BR-04)", async () => {
    const resolve = vi.fn().mockResolvedValue(versioned(invoiceFixture({ status: "MATCHING" })));
    renderPage(
      fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(claimedBy(MEMBER))), resolve }),
    );
    await userEvent.setup().click(await screen.findByRole("button", { name: "Accept as is" }));
    expect(resolve).toHaveBeenCalledWith("inv-12", 'W/"1"');
    expect(
      await screen.findByText("Accepted. Matching runs again; the invoice is posted when it passes."),
    ).toBeInTheDocument();
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
