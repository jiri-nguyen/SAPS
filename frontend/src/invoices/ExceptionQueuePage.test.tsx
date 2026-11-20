import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { MEMBER, fakeExceptionApi, summary } from "../test/invoices";
import { ExceptionQueuePage } from "./ExceptionQueuePage";

const page = (items = [summary()], nextPageToken: string | null = null) => ({ items, nextPageToken });

describe("ExceptionQueuePage", () => {
  it("lists unclaimed invoices first, then mine", async () => {
    const list = vi
      .fn()
      .mockResolvedValueOnce(page())
      .mockResolvedValueOnce(
        page([summary({ id: "inv-9", assignedTo: { id: MEMBER.id, displayName: "Accounting Member 1" } })]),
      );
    render(<ExceptionQueuePage api={fakeExceptionApi({ list })} role="ACCOUNTING_MEMBER" />);
    const row = await screen.findByTestId("queue-row");
    expect(row).toHaveTextContent("Alpha Office Supplies Co.");
    expect(row).toHaveTextContent("90.64");
    expect(within(row).getByText("EX6")).toHaveAttribute("title", "Unit price outside tolerance");
    expect(within(row).getByRole("link", { name: "AOS-2026-1013" })).toHaveAttribute(
      "href",
      "#/invoices/inv-12",
    );
    expect(list).toHaveBeenLastCalledWith({ status: ["EXCEPTION"], assignee: "unassigned" });

    await userEvent.setup().click(screen.getByRole("tab", { name: "Mine" }));
    expect(await screen.findByText("Accounting Member 1")).toBeInTheDocument();
    expect(list).toHaveBeenLastCalledWith({ status: ["EXCEPTION"], assignee: "me" });
    expect(screen.getByRole("tab", { name: "Mine" })).toHaveAttribute("aria-selected", "true");
    expect(screen.queryByRole("button", { name: "Claim" })).not.toBeInTheDocument(); // already claimed
  });

  it("claims and opens the invoice", async () => {
    const claim = vi.fn().mockResolvedValue(undefined);
    render(
      <ExceptionQueuePage
        api={fakeExceptionApi({ list: vi.fn().mockResolvedValue(page()), claim })}
        role="ACCOUNTING_MEMBER"
      />,
    );
    await userEvent.setup().click(await screen.findByRole("button", { name: "Claim" }));
    expect(claim).toHaveBeenCalledWith("inv-12");
    await waitFor(() => expect(window.location.hash).toBe("#/invoices/inv-12"));
  });

  it("explains a lost claim race and refreshes the list", async () => {
    const list = vi.fn().mockResolvedValueOnce(page()).mockResolvedValueOnce(page([]));
    const claim = vi.fn().mockRejectedValue(
      new ApiError(409, {
        type: "about:blank",
        title: "Conflict",
        status: 409,
        detail: "The invoice is already claimed by another member.",
      }),
    );
    render(<ExceptionQueuePage api={fakeExceptionApi({ list, claim })} role="ACCOUNTING_MEMBER" />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Claim" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("already claimed by another member");
    await waitFor(() => expect(screen.queryAllByTestId("queue-row")).toHaveLength(0)); // list refreshed
    expect(list).toHaveBeenCalledTimes(2);
  });

  it("loads more pages and refreshes on request", async () => {
    const list = vi
      .fn()
      .mockResolvedValueOnce(page([summary()], "next-1"))
      .mockResolvedValueOnce(page([summary({ id: "inv-2", invoiceNumber: "AOS-2" })]))
      .mockResolvedValueOnce(page([]));
    render(<ExceptionQueuePage api={fakeExceptionApi({ list })} role="ACCOUNTING_MEMBER" />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Load more" }));
    expect(await screen.findByText("AOS-2")).toBeInTheDocument();
    expect(screen.getAllByTestId("queue-row")).toHaveLength(2);
    expect(list).toHaveBeenNthCalledWith(2, {
      status: ["EXCEPTION"],
      assignee: "unassigned",
      pageToken: "next-1",
    });
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Refresh" }));
    expect(await screen.findByText("No invoices in this queue.")).toBeInTheDocument();
  });

  it("shows load errors", async () => {
    const list = vi
      .fn()
      .mockResolvedValueOnce(page([summary()], "next-1"))
      .mockRejectedValueOnce(new Error("offline"));
    render(<ExceptionQueuePage api={fakeExceptionApi({ list })} role="ACCOUNTING_MEMBER" />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Load more" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Check the connection");
  });

  it("shows the first load error", async () => {
    const list = vi
      .fn()
      .mockRejectedValue(
        new ApiError(500, { type: "about:blank", title: "x", status: 500, detail: "Boom." }),
      );
    render(<ExceptionQueuePage api={fakeExceptionApi({ list })} role="ACCOUNTING_MEMBER" />);
    expect(await screen.findByRole("alert")).toHaveTextContent("Boom.");
  });

  it("is read-only for an Accounting Manager", async () => {
    const list = vi
      .fn()
      .mockResolvedValue(
        page([
          summary(),
          summary({ id: "inv-3", assignedTo: { id: "x", displayName: "Accounting Member 2" } }),
        ]),
      );
    render(<ExceptionQueuePage api={fakeExceptionApi({ list })} role="ACCOUNTING_MANAGER" />);
    expect(await screen.findAllByTestId("queue-row")).toHaveLength(2);
    expect(list).toHaveBeenCalledWith({ status: ["EXCEPTION"], assignee: undefined });
    expect(screen.queryByRole("tab")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Claim" })).not.toBeInTheDocument();
    expect(screen.getByText(/Read only/)).toBeInTheDocument();
  });

  it("ignores a response that arrives after leaving the page", async () => {
    let resolve: (value: ReturnType<typeof page>) => void = () => {};
    const { unmount } = render(
      <ExceptionQueuePage
        api={fakeExceptionApi({ list: () => new Promise((r) => (resolve = r)) })}
        role="ACCOUNTING_MEMBER"
      />,
    );
    unmount();
    resolve(page());
    await Promise.resolve();
  });
});
