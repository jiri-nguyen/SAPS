import { type ChangeEvent, type DragEvent, useEffect, useState } from "react";

import { ApiError } from "../api/client";
import type { Invoice, InvoiceApi, InvoiceStatus } from "../api/invoices";

const STATUS_LABEL: Record<InvoiceStatus, string> = {
  UPLOADED: "Uploaded",
  MATCHING: "Matching",
  EXCEPTION: "Exception",
  PENDING_APPROVAL: "Pending approval",
  PENDING_REVIEW: "Pending review",
  COMPLETED: "Completed",
  REJECTED: "Rejected",
};

/** Statuses the SAPS Worker still changes; the page polls getInvoice while an invoice is in one (BR-08). */
const PROCESSING: ReadonlySet<InvoiceStatus> = new Set(["UPLOADED", "MATCHING"]);
const ACCEPT = ".pdf,.jpg,.jpeg,.png,application/pdf,image/jpeg,image/png";

interface Row {
  rowId: number;
  file: File;
  key: string;
  progress: number;
  invoice?: Invoice;
  error?: string;
}

function formatSize(bytes: number): string {
  return bytes < 1024 * 1024
    ? `${Math.max(1, Math.round(bytes / 1024))} KB`
    : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

function errorText(error: unknown): string {
  if (error instanceof ApiError && error.status !== 0) return error.message;
  return "The upload failed. Check the connection and try again.";
}

let nextRowId = 1;

export function UploadPage({
  api,
  pollMs = 2000,
  newKey = () => crypto.randomUUID(),
}: {
  api: InvoiceApi;
  pollMs?: number;
  newKey?: () => string;
}) {
  const [rows, setRows] = useState<Row[]>([]);
  const [dragging, setDragging] = useState(false);

  const update = (rowId: number, change: Partial<Row>) =>
    setRows((current) => current.map((row) => (row.rowId === rowId ? { ...row, ...change } : row)));

  function send(row: Row) {
    update(row.rowId, { progress: 0, error: undefined });
    api
      .upload(row.file, row.key, (progress) => update(row.rowId, { progress }))
      .then(
        (invoice) => update(row.rowId, { invoice, progress: 1 }),
        (error: unknown) => update(row.rowId, { error: errorText(error) }),
      );
  }

  function addFiles(files: FileList | null) {
    if (files === null) return;
    // One Idempotency-Key per file; a retry reuses it, so a lost answer never creates a second invoice (BR-06).
    const added = Array.from(files).map((file) => ({ rowId: nextRowId++, file, key: newKey(), progress: 0 }));
    setRows((current) => [...added, ...current]);
    added.forEach(send);
  }

  const polling = rows
    .filter((row) => row.invoice !== undefined && PROCESSING.has(row.invoice.status))
    .map((row) => row.invoice?.id)
    .join(",");

  useEffect(() => {
    if (polling === "") return;
    const timer = setInterval(() => {
      for (const id of polling.split(",")) {
        api.get(id).then(
          (invoice) =>
            setRows((current) =>
              current.map((row) => (row.invoice?.id === invoice.id ? { ...row, invoice } : row)),
            ),
          () => {}, // try again on the next tick; a 401 returns to the sign-in page
        );
      }
    }, pollMs);
    return () => clearInterval(timer);
  }, [polling, api, pollMs]);

  function onDrop(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    setDragging(false);
    addFiles(event.dataTransfer.files);
  }

  return (
    <section aria-label="Upload invoices">
      <div
        data-testid="drop-zone"
        className={dragging ? "drop-zone dragging" : "drop-zone"}
        onDragOver={(event) => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
      >
        <p>Drop PDF, JPEG or PNG files here, or</p>
        <label>
          Choose files
          <input
            type="file"
            multiple
            accept={ACCEPT}
            onChange={(event: ChangeEvent<HTMLInputElement>) => {
              addFiles(event.target.files);
              event.target.value = "";
            }}
          />
        </label>
      </div>
      {rows.length > 0 && (
        <table>
          <thead>
            <tr>
              <th>File</th>
              <th>Size</th>
              <th>Status</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.rowId} data-testid="upload-row">
                <td>{row.file.name}</td>
                <td>{formatSize(row.file.size)}</td>
                <td>
                  {row.error !== undefined ? (
                    <span role="alert">Failed: {row.error}</span>
                  ) : row.invoice !== undefined ? (
                    STATUS_LABEL[row.invoice.status]
                  ) : (
                    <progress max={1} value={row.progress} aria-label={`Uploading ${row.file.name}`} />
                  )}
                </td>
                <td>
                  {row.error !== undefined && (
                    <button type="button" onClick={() => send(row)}>
                      Retry
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
