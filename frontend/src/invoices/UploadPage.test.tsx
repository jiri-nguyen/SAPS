import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import type { Invoice, InvoiceApi, InvoiceStatus } from "../api/invoices";
import { UploadPage } from "./UploadPage";

const invoice = (id: string, status: InvoiceStatus) => ({ id, status }) as Invoice;
const pdf = (name = "a.pdf", size = 2048) =>
  new File([new Uint8Array(size)], name, { type: "application/pdf" });

function keys() {
  let n = 0;
  return () => `key-${++n}`;
}

async function choose(...files: File[]) {
  await userEvent.setup().upload(screen.getByLabelText("Choose files"), files);
}

describe("UploadPage", () => {
  it("uploads each file with its own key and shows progress, then the status", async () => {
    let finish: (value: Invoice) => void = () => {};
    const upload = vi.fn((_file: File, _key: string, onProgress: (p: number) => void) => {
      onProgress(0.4);
      return new Promise<Invoice>((resolve) => (finish = resolve));
    });
    render(<UploadPage api={{ upload, get: vi.fn() }} newKey={keys()} pollMs={100_000} />);
    await choose(pdf("a.pdf"), pdf("b.pdf", 3 * 1024 * 1024));
    expect(upload.mock.calls.map((call) => call[1])).toEqual(["key-1", "key-2"]);
    expect(screen.getByLabelText("Uploading a.pdf")).toHaveValue(0.4);
    expect(screen.getByText("3.0 MB")).toBeInTheDocument();
    expect(screen.getByText("2 KB")).toBeInTheDocument();
    act(() => finish(invoice("inv-2", "UPLOADED")));
    expect(await screen.findByText("Uploaded")).toBeInTheDocument();
  });

  it("polls while the invoice is processed and stops afterwards", async () => {
    const get = vi
      .fn()
      .mockResolvedValue(invoice("inv-1", "EXCEPTION")) // a late tick before the interval stops gets an answer too
      .mockResolvedValueOnce(invoice("inv-1", "MATCHING"))
      .mockRejectedValueOnce(new Error("offline"))
      .mockResolvedValueOnce(invoice("inv-1", "EXCEPTION"));
    const api: InvoiceApi = { upload: vi.fn().mockResolvedValue(invoice("inv-1", "UPLOADED")), get };
    render(<UploadPage api={api} newKey={keys()} pollMs={5} />);
    await choose(pdf());
    expect(await screen.findByText("Exception")).toBeInTheDocument();
    const calls = get.mock.calls.length;
    await new Promise((resolve) => setTimeout(resolve, 30));
    expect(get).toHaveBeenCalledTimes(calls);
    expect(get).toHaveBeenCalledWith("inv-1");
  });

  it("shows the problem detail and retries with the same key", async () => {
    const upload = vi
      .fn()
      .mockRejectedValueOnce(
        new ApiError(415, {
          type: "about:blank",
          title: "x",
          status: 415,
          detail: "Only PDF, JPEG and PNG files are accepted.",
        }),
      )
      .mockRejectedValueOnce(new ApiError(0))
      .mockResolvedValueOnce(invoice("inv-1", "PENDING_REVIEW"));
    render(<UploadPage api={{ upload, get: vi.fn() }} newKey={keys()} />);
    await choose(pdf("fake.pdf"));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Failed: Only PDF, JPEG and PNG files are accepted.",
    );
    await userEvent.setup().click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Check the connection");
    await userEvent.setup().click(screen.getByRole("button", { name: "Retry" }));
    expect(await screen.findByText("Pending review")).toBeInTheDocument();
    expect(upload.mock.calls.map((call) => call[1])).toEqual(["key-1", "key-1", "key-1"]);
  });

  it("accepts dropped files and ignores an empty selection", async () => {
    const upload = vi.fn().mockResolvedValue(invoice("inv-9", "COMPLETED"));
    render(<UploadPage api={{ upload, get: vi.fn() }} newKey={keys()} />);
    const zone = screen.getByTestId("drop-zone");
    fireEvent.dragOver(zone);
    expect(zone).toHaveClass("dragging");
    fireEvent.dragLeave(zone);
    expect(zone).not.toHaveClass("dragging");
    fireEvent.drop(zone, { dataTransfer: { files: [pdf("dropped.pdf")] } });
    expect(await screen.findByText("Completed")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Choose files"), { target: { files: null } });
    await waitFor(() => expect(screen.getAllByTestId("upload-row")).toHaveLength(1));
  });

  it("uses random keys by default", async () => {
    const upload = vi.fn().mockResolvedValue(invoice("inv-1", "REJECTED"));
    render(<UploadPage api={{ upload, get: vi.fn() }} />);
    await choose(pdf());
    expect(await screen.findByText("Rejected")).toBeInTheDocument();
    expect(upload.mock.calls[0]?.[1]).toMatch(/^[0-9a-f-]{36}$/);
  });
});
