import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import type { ExceptionApi } from "../api/exceptions";
import { fakeExceptionApi, summary } from "../test/invoices";
import { InvoiceSearchPage } from "./InvoiceSearchPage";

const MAIL = summary({
  id: "inv-2",
  status: "COMPLETED",
  channel: "MAIL",
  invoiceNumber: "BT 77",
  vendorName: "Beta Tools",
  invoiceDate: null,
  openExceptionCodes: [],
  assignedTo: { id: "u1", displayName: "Accounting Member 1" },
  uploadedAt: "2027-03-01T17:30:00Z",
});

function page(...items: ReturnType<typeof summary>[]) {
  return { items, nextPageToken: null };
}

function renderPage(api: ExceptionApi, query = "") {
  return render(<InvoiceSearchPage api={api} query={query} />);
}

afterEach(() => {
  window.location.hash = "";
});

describe("InvoiceSearchPage", () => {
  it("lists the invoices of every status with the columns of the spec (BR-06)", async () => {
    const list = vi.fn().mockResolvedValue(page(summary(), MAIL));
    renderPage(fakeExceptionApi({ list }));
    const rows = await screen.findAllByTestId("invoice-row");
    expect(rows).toHaveLength(2);
    expect(list).toHaveBeenCalledWith({});
    expect(rows[0]).toHaveTextContent("AOS-2026-1013");
    expect(rows[0]).toHaveTextContent("Alpha Office Supplies Co.");
    expect(rows[0]).toHaveTextContent("2026-12-09");
    expect(rows[0]).toHaveTextContent("90.64");
    expect(rows[0]).toHaveTextContent("Exception");
    expect(rows[0]).toHaveTextContent("Upload");
    expect(rows[0]).toHaveTextContent("2026-12-15 08:30 UTC");
    expect(rows[0]).toHaveTextContent("EX6");
    expect(rows[1]).toHaveTextContent("Completed");
    expect(rows[1]).toHaveTextContent("Mail");
    expect(rows[1]).toHaveTextContent("Accounting Member 1");
    expect(within(rows[1] as HTMLElement).getAllByText("—").length).toBeGreaterThan(0); // no invoice date, no exceptions
  });

  it("opens an invoice with the same filters in the link", async () => {
    renderPage(
      fakeExceptionApi({ list: vi.fn().mockResolvedValue(page(MAIL)) }),
      "vendor=beta&status=COMPLETED",
    );
    expect(await screen.findByRole("link", { name: "BT 77" })).toHaveAttribute(
      "href",
      "#/invoices/inv-2?vendor=beta&status=COMPLETED",
    );
  });

  it("fills the form from the URL and searches with those filters", async () => {
    const list = vi.fn().mockResolvedValue(page());
    renderPage(
      fakeExceptionApi({ list }),
      "status=COMPLETED&status=EXCEPTION&vendor=alpha&poNumber=0100012&channel=MAIL&totalMin=10",
    );
    expect(await screen.findByText("No invoices match these filters.")).toBeInTheDocument();
    expect(list).toHaveBeenCalledWith({
      status: ["COMPLETED", "EXCEPTION"],
      vendor: "alpha",
      poNumber: "0100012",
      channel: "MAIL",
      totalMin: "10",
    });
    expect(screen.getByLabelText("Vendor")).toHaveValue("alpha");
    expect(screen.getByLabelText("PO number")).toHaveValue("0100012");
    expect(screen.getByLabelText("Channel")).toHaveValue("MAIL");
    expect(screen.getByLabelText("Completed")).toBeChecked();
    expect(screen.getByLabelText("Exception")).toBeChecked();
    expect(screen.getByLabelText("Uploaded")).not.toBeChecked();
  });

  it("puts the filters into the URL when searching, leaving empty ones out", async () => {
    renderPage(fakeExceptionApi({ list: vi.fn().mockResolvedValue(page()) }));
    const person = userEvent.setup();
    await screen.findByText("No invoices match these filters.");
    await person.type(screen.getByLabelText("Vendor"), "  alpha ");
    await person.type(screen.getByLabelText("Invoice number"), "AOS 2026");
    await person.type(screen.getByLabelText("Invoice date from"), "2027-01-01");
    await person.click(screen.getByLabelText("Completed"));
    await person.click(screen.getByLabelText("Rejected"));
    await person.click(screen.getByLabelText("Rejected")); // unchecked again
    await person.selectOptions(screen.getByLabelText("Channel"), "UPLOAD");
    await person.click(screen.getByRole("button", { name: "Search" }));
    expect(window.location.hash).toBe(
      "#/invoices?status=COMPLETED&vendor=alpha&invoiceNumber=AOS+2026&invoiceDateFrom=2027-01-01&channel=UPLOAD",
    );
  });

  it("searches again when the filters did not change, and clears them", async () => {
    const list = vi.fn().mockResolvedValue(page());
    renderPage(fakeExceptionApi({ list }), "vendor=alpha");
    const person = userEvent.setup();
    await screen.findByText("No invoices match these filters.");
    await person.click(screen.getByRole("button", { name: "Search" }));
    await vi.waitFor(() => expect(list).toHaveBeenCalledTimes(2)); // the same URL: a refresh
    window.location.hash = "#/invoices?vendor=alpha";
    await person.click(screen.getByRole("button", { name: "Clear" }));
    expect(window.location.hash).toBe("#/invoices");
    expect(screen.getByLabelText("Vendor")).toHaveValue("");
  });

  it("loads more pages with the same filters", async () => {
    const list = vi
      .fn()
      .mockResolvedValueOnce({ items: [summary()], nextPageToken: "t1" })
      .mockResolvedValueOnce({ items: [MAIL], nextPageToken: null });
    renderPage(fakeExceptionApi({ list }), "vendor=a");
    await screen.findByTestId("invoice-row");
    await userEvent.setup().click(await screen.findByRole("button", { name: "Load more" }));
    expect(await screen.findAllByTestId("invoice-row")).toHaveLength(2);
    expect(list).toHaveBeenLastCalledWith({ vendor: "a", pageToken: "t1" });
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });

  it("marks the refused filters and keeps the form (BR-07)", async () => {
    const problem = {
      type: "about:blank",
      title: "Bad Request",
      status: 400,
      errors: [
        { field: "totalMin", message: "totalMin must not be after totalMax." },
        { field: "poNumber", message: "String should match pattern" },
      ],
    };
    const list = vi.fn().mockRejectedValue(new ApiError(400, problem));
    renderPage(fakeExceptionApi({ list }), "totalMin=10&totalMax=9&poNumber=12");
    expect(await screen.findByText("Correct the marked filters.")).toBeInTheDocument();
    expect(screen.getByText("totalMin must not be after totalMax.")).toBeInTheDocument();
    expect(screen.getByText("String should match pattern")).toBeInTheDocument();
    expect(screen.getByLabelText(/Total from/)).toHaveAttribute("aria-invalid", "true");
    expect(screen.getByLabelText(/Total from/)).toHaveValue("10");
    expect(screen.queryByText("No invoices match these filters.")).not.toBeInTheDocument();
  });

  it("shows other errors as a message, also when loading more fails", async () => {
    renderPage(fakeExceptionApi({ list: vi.fn().mockRejectedValue(new ApiError(500)) }));
    expect(await screen.findByRole("alert")).toHaveTextContent("HTTP 500");

    const list = vi
      .fn()
      .mockResolvedValueOnce({ items: [summary()], nextPageToken: "t1" })
      .mockRejectedValueOnce(new Error("offline"));
    renderPage(fakeExceptionApi({ list }));
    await userEvent.setup().click(await screen.findByRole("button", { name: "Load more" }));
    expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
  });

  it("ignores an answer that arrives after the screen was left", async () => {
    let resolve: (value: ReturnType<typeof page>) => void = () => {};
    const { unmount } = renderPage(
      fakeExceptionApi({ list: vi.fn().mockReturnValue(new Promise((r) => (resolve = r))) }),
    );
    unmount();
    resolve(page(summary()));
    await Promise.resolve();
    expect(screen.queryByTestId("invoice-row")).not.toBeInTheDocument();
  });
});
