import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import type { ExceptionApi } from "../api/exceptions";
import type { Invoice } from "../api/invoices";
import { MANAGER, MEMBER, fakeExceptionApi, invoiceFixture, versioned } from "../test/invoices";
import { InvoiceDetailPage } from "./InvoiceDetailPage";

/** DS-08: a non-PO invoice above the threshold whose EX2 a member accepted as is. */
function waitingInvoice(overrides: Partial<Invoice> = {}): Invoice {
  const [ex] = invoiceFixture().exceptions;
  return invoiceFixture({
    status: "PENDING_APPROVAL",
    totalAmount: "450.00",
    exceptions: [
      {
        ...(ex as NonNullable<typeof ex>),
        id: "ex-2",
        code: "EX2",
        message: "Non-PO invoice: manual review is required.",
        status: "RESOLVED",
        invoiceLineId: null,
        resolvedBy: { id: MEMBER.id, displayName: MEMBER.displayName },
        resolvedAt: "2026-12-15T09:30:00Z",
      },
    ],
    ...overrides,
  });
}

function render_(api: ExceptionApi, user = MANAGER, queue: "approvals" | "exceptions" = "approvals") {
  return render(<InvoiceDetailPage api={api} invoiceId="inv-12" user={user} queue={queue} />);
}

const problem = (status: number, detail: string) =>
  new ApiError(status, { type: "about:blank", title: "x", status, detail });

describe("approval on the invoice page (SAPS-22)", () => {
  it("shows the manager what was accepted as is, and who accepted it", async () => {
    render_(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(waitingInvoice())) }));
    expect(await screen.findByText("This invoice waits for your decision.")).toBeInTheDocument();
    expect(screen.getByText(/Non-PO invoice: manual review is required/)).toBeInTheDocument();
    expect(screen.getByText(/resolved by Accounting Member 1 on 2026-12-15 09:30 UTC/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← Approval queue" })).toHaveAttribute("href", "#/approvals");
    expect(screen.queryByText(/Non-PO invoice: Non-PO invoice/)).not.toBeInTheDocument(); // the title is not repeated
    expect(screen.queryByText(/Claimed by/)).not.toBeInTheDocument(); // only meaningful in exception handling
    expect(screen.queryByRole("button", { name: "Correct data" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Accept as is" })).not.toBeInTheDocument();
  });

  it("approves and names the next step", async () => {
    const decide = vi.fn().mockResolvedValue(versioned(invoiceFixture({ status: "PENDING_REVIEW" })));
    render_(
      fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(waitingInvoice())), decide }),
    );
    await userEvent.setup().click(await screen.findByRole("button", { name: "Approve" }));
    expect(decide).toHaveBeenCalledWith("inv-12", "APPROVED");
    expect(await screen.findByText("Approved. Next step: Pending review.")).toBeInTheDocument();
  });

  it("rejects with a comment, and asks for one first", async () => {
    const decide = vi.fn().mockResolvedValue(versioned(invoiceFixture({ status: "REJECTED" })));
    render_(
      fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(waitingInvoice())), decide }),
    );
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Reject" }));
    await user.click(screen.getByRole("button", { name: "Reject invoice" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Enter the reason for the rejection.");
    expect(decide).not.toHaveBeenCalled();
    await user.type(screen.getByRole("textbox", { name: "Reason" }), "  Price is not agreed. ");
    await user.click(screen.getByRole("button", { name: "Reject invoice" }));
    expect(decide).toHaveBeenCalledWith("inv-12", "REJECTED", "Price is not agreed.");
    expect(await screen.findByText("The invoice was rejected.")).toBeInTheDocument();
  });

  it("says when another manager decided first", async () => {
    const decide = vi
      .fn()
      .mockRejectedValue(problem(409, "The invoice does not wait for approval (status Pending review)."));
    const getVersioned = vi
      .fn()
      .mockResolvedValueOnce(versioned(waitingInvoice()))
      .mockResolvedValue(versioned(invoiceFixture({ status: "PENDING_REVIEW" })));
    render_(fakeExceptionApi({ getVersioned, decide }));
    await userEvent.setup().click(await screen.findByRole("button", { name: "Approve" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "does not wait for approval (status Pending review)",
    );
    expect(
      await screen.findByText("This invoice waits for the final review by an Accounting Member."),
    ).toBeInTheDocument(); // the other manager approved it: next step SAPS-21
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
  });

  it("shows a member that the invoice waits for a manager, with no decision buttons", async () => {
    render_(
      fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(waitingInvoice())) }),
      MEMBER,
      "exceptions",
    );
    expect(
      await screen.findByText("This invoice waits for approval by an Accounting Manager."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Approve" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← Exception queue" })).toBeInTheDocument();
  });

  it("shows the decision that was made, with its comment", async () => {
    const decided = waitingInvoice({
      status: "REJECTED",
      approval: {
        id: "a1",
        decision: "REJECTED",
        comment: "Price is not agreed.",
        decidedBy: { id: MANAGER.id, displayName: MANAGER.displayName },
        decidedAt: "2026-12-15T10:00:00Z",
      },
    });
    render_(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(decided)) }));
    expect(
      await screen.findByText(
        /Rejected by Accounting Manager 1 on 2026-12-15 10:00 UTC: Price is not agreed\./,
      ),
    ).toBeInTheDocument();
    const approved = waitingInvoice({
      status: "PENDING_REVIEW",
      approval: {
        id: "a2",
        decision: "APPROVED",
        comment: null,
        decidedBy: { id: MANAGER.id, displayName: "Accounting Manager 1" },
        decidedAt: "2026-12-15T10:00:00Z",
      },
    });
    render_(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(approved)) }));
    expect(
      await screen.findByText(/Approved by Accounting Manager 1 on 2026-12-15 10:00 UTC$/),
    ).toBeInTheDocument();
  });
});
