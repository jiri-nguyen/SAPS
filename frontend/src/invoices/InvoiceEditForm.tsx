import { type FormEvent, useState } from "react";

import type { InvoiceUpdate } from "../api/exceptions";
import type { Invoice } from "../api/invoices";
import {
  HEADER_FIELDS,
  type HeaderKey,
  type LineValues,
  changes,
  emptyLine,
  headerOf,
  linesOf,
  validate,
} from "./edit-model";

const LINE_COLUMNS: readonly { key: keyof LineValues; label: string }[] = [
  { key: "lineNumber", label: "Line" },
  { key: "description", label: "Description" },
  { key: "poNumber", label: "PO number" },
  { key: "poLineNumber", label: "PO line" },
  { key: "quantity", label: "Quantity" },
  { key: "unitPrice", label: "Unit price" },
  { key: "lineAmount", label: "Line amount" },
];

/** Correct header fields and lines (SAPS-20 BR-04); a matching-field change sends the invoice to re-matching. */
export function InvoiceEditForm({
  invoice,
  busy,
  onSave,
  onCancel,
}: {
  invoice: Invoice;
  busy: boolean;
  onSave: (body: InvoiceUpdate) => void;
  onCancel: () => void;
}) {
  const [original] = useState(() => ({ header: headerOf(invoice), lines: linesOf(invoice) }));
  const [header, setHeader] = useState(original.header);
  const [lines, setLines] = useState<LineValues[]>(() =>
    original.lines.length > 0 ? original.lines : [emptyLine([])],
  );
  const [errors, setErrors] = useState<string[]>([]);

  const setLine = (index: number, key: keyof LineValues, value: string) =>
    setLines((current) => current.map((line, i) => (i === index ? { ...line, [key]: value } : line)));

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const found = validate(original.header, header, lines);
    if (found.length > 0) {
      setErrors(found);
      return;
    }
    const body = changes(original, header, lines);
    if (Object.keys(body).length === 0) {
      setErrors(["Nothing changed."]);
      return;
    }
    setErrors([]);
    onSave(body);
  }

  return (
    <form className="edit stack" aria-label="Correct invoice data" onSubmit={submit}>
      <fieldset className="grid">
        <legend>Header</legend>
        {HEADER_FIELDS.map((field) => (
          <label key={field.key}>
            {field.label}
            <input
              name={field.key}
              type={field.key === "invoiceDate" ? "date" : "text"}
              value={header[field.key]}
              onChange={(e) => setHeader((h) => ({ ...h, [field.key as HeaderKey]: e.target.value }))}
            />
          </label>
        ))}
      </fieldset>
      <fieldset>
        <legend>Lines</legend>
        <table className="data edit-lines">
          <thead>
            <tr>
              {LINE_COLUMNS.map((column) => (
                <th key={column.key}>{column.label}</th>
              ))}
              <th />
            </tr>
          </thead>
          <tbody>
            {lines.map((line, index) => (
              <tr key={index}>
                {LINE_COLUMNS.map((column) => (
                  <td key={column.key}>
                    <input
                      aria-label={`${column.label}, row ${index + 1}`}
                      value={line[column.key]}
                      onChange={(e) => setLine(index, column.key, e.target.value)}
                    />
                  </td>
                ))}
                <td>
                  <button
                    type="button"
                    className="secondary"
                    disabled={lines.length === 1}
                    onClick={() => setLines((current) => current.filter((_, i) => i !== index))}
                  >
                    Remove
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button
          type="button"
          className="secondary"
          onClick={() => setLines((current) => [...current, emptyLine(current)])}
        >
          Add line
        </button>
      </fieldset>
      {errors.length > 0 && (
        <ul role="alert" className="banner error">
          {errors.map((error) => (
            <li key={error}>{error}</li>
          ))}
        </ul>
      )}
      <div className="actions">
        <button type="submit" className="primary" disabled={busy}>
          Save
        </button>
        <button type="button" className="secondary" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
