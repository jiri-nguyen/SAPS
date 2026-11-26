import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import type { ExceptionApi } from "../api/exceptions";
import { fakeExceptionApi, summary } from "../test/invoices";
import { StatusQueuePage } from "./StatusQueuePage";

const waiting = (overrides = {}) =>
  summary({ status: "PENDING_APPROVAL", openExceptionCodes: [], ...overrides });
const page = (items = [waiting()], nextPageToken: string | null = null) => ({ items, nextPageToken });

function ApprovalQueuePage({ api }: { api: ExceptionApi }) {
  return (
    <StatusQueuePage
      api={api}
      status="PENDING_APPROVAL"
      queue="approvals"
      label="Approval queue"
      emptyText="No invoices wait for approval."
    />
  );
}

describe("StatusQueuePage", () => {
  it("lists the invoices that wait for approval and links to them", async () => {
    const list = vi
      .fn()
      .mockResolvedValue(page([waiting({ totalAmount: "495.00", invoiceType: "TRADE_PO" })]));
    render(<ApprovalQueuePage api={fakeExceptionApi({ list })} />);
    const row = await screen.findByTestId("status-row");
    expect(row).toHaveTextContent("Alpha Office Supplies Co.");
    expect(row).toHaveTextContent("495.00");
    expect(row).toHaveTextContent("TRADE_PO");
    expect(screen.getByRole("link", { name: "AOS-2026-1013" })).toHaveAttribute("href", "#/approvals/inv-12");
    expect(list).toHaveBeenCalledWith({ status: ["PENDING_APPROVAL"] });
  });

  it("says when nothing waits, and refreshes", async () => {
    const list = vi.fn().mockResolvedValueOnce(page([])).mockResolvedValueOnce(page());
    render(<ApprovalQueuePage api={fakeExceptionApi({ list })} />);
    expect(await screen.findByText("No invoices wait for approval.")).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("button", { name: "Refresh" }));
    expect(await screen.findByTestId("status-row")).toBeInTheDocument();
  });

  it("loads more pages", async () => {
    const list = vi
      .fn()
      .mockResolvedValueOnce(page([waiting()], "next-1"))
      .mockResolvedValueOnce(page([waiting({ id: "inv-2", invoiceNumber: "AOS-2" })]));
    render(<ApprovalQueuePage api={fakeExceptionApi({ list })} />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Load more" }));
    expect(await screen.findByText("AOS-2")).toBeInTheDocument();
    expect(list).toHaveBeenLastCalledWith({ status: ["PENDING_APPROVAL"], pageToken: "next-1" });
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });

  it("shows load errors", async () => {
    const failing = vi
      .fn()
      .mockRejectedValue(
        new ApiError(500, { type: "about:blank", title: "x", status: 500, detail: "Boom." }),
      );
    const { unmount } = render(<ApprovalQueuePage api={fakeExceptionApi({ list: failing })} />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Boom.");
    unmount();
    const list = vi
      .fn()
      .mockResolvedValueOnce(page([waiting()], "next-1"))
      .mockRejectedValueOnce(new Error("offline"));
    render(<ApprovalQueuePage api={fakeExceptionApi({ list })} />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Load more" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Check the connection");
  });

  it("ignores a response that arrives after leaving the page", async () => {
    let resolve: (value: ReturnType<typeof page>) => void = () => {};
    const { unmount } = render(
      <ApprovalQueuePage api={fakeExceptionApi({ list: () => new Promise((r) => (resolve = r)) })} />,
    );
    unmount();
    resolve(page());
    await Promise.resolve();
  });

  it("serves a queue with its own status, links and empty text", async () => {
    const list = vi
      .fn()
      .mockResolvedValueOnce(page([]))
      .mockResolvedValueOnce(page([summary({ status: "PENDING_REVIEW" })]));
    const api = fakeExceptionApi({ list });
    const { rerender } = render(
      <StatusQueuePage
        api={api}
        status="PENDING_REVIEW"
        queue="review"
        label="Review queue"
        emptyText="Nothing to review."
      />,
    );
    expect(await screen.findByText("Nothing to review.")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "Review queue" })).toBeInTheDocument();
    expect(list).toHaveBeenCalledWith({ status: ["PENDING_REVIEW"] });
    rerender(
      <StatusQueuePage
        api={api}
        status="COMPLETED"
        queue="review"
        label="Review queue"
        emptyText="Nothing to review."
      />,
    );
    expect(await screen.findByRole("link", { name: "AOS-2026-1013" })).toHaveAttribute(
      "href",
      "#/review/inv-12",
    );
    expect(list).toHaveBeenLastCalledWith({ status: ["COMPLETED"] });
  });
});
