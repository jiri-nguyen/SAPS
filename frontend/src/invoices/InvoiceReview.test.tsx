import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import type { ExceptionApi } from "../api/exceptions";
import { MANAGER, MEMBER, OTHER, fakeExceptionApi, invoiceFixture, versioned } from "../test/invoices";
import { InvoiceDetailPage } from "./InvoiceDetailPage";

const reviewable = () =>
  invoiceFixture({
    status: "PENDING_REVIEW",
    approval: {
      id: "a1",
      decision: "APPROVED",
      comment: null,
      decidedBy: { id: MANAGER.id, displayName: MANAGER.displayName },
      decidedAt: "2026-12-15T10:00:00Z",
    },
  });

function show(api: ExceptionApi, user = OTHER) {
  return render(<InvoiceDetailPage api={api} invoiceId="inv-12" user={user} queue="review" />);
}

describe("final review on the invoice page (SAPS-21)", () => {
  it("shows any member the result, the approval and the review actions, without edit controls", async () => {
    show(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(reviewable())) }));
    expect(await screen.findByText(/waits for your final review/)).toBeInTheDocument();
    expect(screen.getByText(/Approved by Accounting Manager 1/)).toBeInTheDocument(); // BR-05
    expect(screen.queryByText("None.")).not.toBeInTheDocument(); // the fixture has an exception
    expect(screen.getByRole("button", { name: "Confirm" })).toBeEnabled();
    expect(screen.getByRole("button", { name: "Reject" })).toBeEnabled();
    expect(screen.queryByRole("button", { name: "Correct data" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Claim" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "← Review queue" })).toHaveAttribute("href", "#/review");
  });

  it("confirms the result", async () => {
    const confirm = vi.fn().mockResolvedValue(versioned(invoiceFixture({ status: "COMPLETED" })));
    show(
      fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(reviewable())), confirm }),
      MEMBER,
    );
    await userEvent.setup().click(await screen.findByRole("button", { name: "Confirm" }));
    expect(confirm).toHaveBeenCalledWith("inv-12");
    expect(
      await screen.findByText("Confirmed. The invoice is completed and ready for posting."),
    ).toBeInTheDocument();
  });

  it("rejects with a reason through rejectInvoice", async () => {
    const reject = vi.fn().mockResolvedValue(versioned(invoiceFixture({ status: "REJECTED" })));
    const api = fakeExceptionApi({
      getVersioned: vi.fn().mockResolvedValue(versioned(reviewable())),
      reject,
    });
    show(api);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Reject" }));
    await user.type(screen.getByRole("textbox", { name: "Reason" }), "Delivered to the wrong site.");
    await user.click(screen.getByRole("button", { name: "Reject invoice" }));
    expect(reject).toHaveBeenCalledWith("inv-12", "Delivered to the wrong site.");
    expect(api.decide).not.toHaveBeenCalled();
    expect(await screen.findByText("The invoice was rejected.")).toBeInTheDocument();
  });

  it("says when another member acted first", async () => {
    const confirm = vi.fn().mockRejectedValue(
      new ApiError(409, {
        type: "about:blank",
        title: "x",
        status: 409,
        detail: "The invoice does not wait for the final review (status Rejected).",
      }),
    );
    const getVersioned = vi
      .fn()
      .mockResolvedValueOnce(versioned(reviewable()))
      .mockResolvedValue(versioned(invoiceFixture({ status: "REJECTED", rejectedReason: "Wrong site." })));
    show(fakeExceptionApi({ getVersioned, confirm }));
    await userEvent.setup().click(await screen.findByRole("button", { name: "Confirm" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("does not wait for the final review");
    expect(await screen.findByText("This invoice is Rejected: Wrong site.")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm" })).not.toBeInTheDocument();
  });

  it("shows a manager the review step without actions", async () => {
    show(fakeExceptionApi({ getVersioned: vi.fn().mockResolvedValue(versioned(reviewable())) }), MANAGER);
    expect(
      await screen.findByText("This invoice waits for the final review by an Accounting Member."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Confirm" })).not.toBeInTheDocument();
  });

  it("shows final states", async () => {
    const { unmount } = show(
      fakeExceptionApi({
        getVersioned: vi
          .fn()
          .mockResolvedValue(versioned(invoiceFixture({ status: "COMPLETED", exceptions: [] }))),
      }),
    );
    expect(await screen.findByText("This invoice is Completed: ready for posting.")).toBeInTheDocument();
    expect(screen.getByText("None.")).toBeInTheDocument(); // no exceptions
    unmount();
    show(
      fakeExceptionApi({
        getVersioned: vi
          .fn()
          .mockResolvedValue(versioned(invoiceFixture({ status: "REJECTED", rejectedReason: null }))),
      }),
    );
    expect(await screen.findByText("This invoice is Rejected.")).toBeInTheDocument();
  });
});
