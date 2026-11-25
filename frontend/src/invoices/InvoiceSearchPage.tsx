import { type FormEvent, useEffect, useState } from "react";

import { ApiError } from "../api/client";
import {
  type ExceptionApi,
  type InvoiceSummary,
  type SearchFilters,
  filterParams,
  parseFilters,
} from "../api/exceptions";
import type { InvoiceStatus } from "../api/invoices";
import { detailPath, href, navigate } from "../routing";
import { errorMessage } from "./errors";
import { STATUS_LABEL, decimal, text, timestamp } from "./format";

const STATUSES = Object.keys(STATUS_LABEL) as InvoiceStatus[];
const CHANNEL_LABEL = { UPLOAD: "Upload", MAIL: "Mail" } as const;
const EMPTY_TEXT = "No invoices match these filters.";

type FieldName = Exclude<keyof SearchFilters, "status">;

/** The field errors of a refused search (`400` with `errors`, SAPS-46 BR-07), by field name. */
function fieldErrors(caught: unknown): Partial<Record<string, string>> {
  if (!(caught instanceof ApiError) || caught.status !== 400) return {};
  const found: Partial<Record<string, string>> = {};
  for (const { field, message } of caught.problem?.errors ?? []) {
    if (field && message) found[field] = message;
  }
  return found;
}

function TextField({
  name,
  label,
  value,
  error,
  onChange,
  type = "text",
  hint,
}: {
  name: FieldName;
  label: string;
  value: string;
  error: string | undefined;
  onChange: (name: FieldName, value: string) => void;
  type?: "text" | "date";
  hint?: string;
}) {
  return (
    <label>
      {label}
      <input
        name={name}
        type={type}
        value={value}
        placeholder={hint}
        aria-invalid={error ? true : undefined}
        onChange={(e) => onChange(name, e.target.value)}
      />
      {error && (
        <span role="alert" className="field-error">
          {error}
        </span>
      )}
    </label>
  );
}

/**
 * "All invoices" (SAPS-46, DEC-057): every invoice of the user's company in every status, with filters. The filters live
 * in the URL (`#/invoices?vendor=alpha`), so reload, Back and links keep the search; an invoice opens with the same
 * query, so "← All invoices" returns to the same results.
 */
export function InvoiceSearchPage({ api, query }: { api: ExceptionApi; query: string }) {
  const [form, setForm] = useState<SearchFilters>(() => parseFilters(query));
  const [refresh, setRefresh] = useState(0);
  const [items, setItems] = useState<InvoiceSummary[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [problems, setProblems] = useState<Partial<Record<string, string>>>({});

  useEffect(() => {
    let active = true;
    api.list(parseFilters(query)).then(
      (page) => {
        if (!active) return;
        setItems(page.items);
        setNext(page.nextPageToken ?? null);
        setError(null);
        setProblems({});
        setLoading(false);
      },
      (caught: unknown) => {
        if (!active) return;
        const fields = fieldErrors(caught);
        setProblems(fields);
        setError(Object.keys(fields).length > 0 ? "Correct the marked filters." : errorMessage(caught));
        setLoading(false);
      },
    );
    return () => {
      active = false;
    };
  }, [api, query, refresh]);

  function change(name: FieldName, value: string) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  function toggleStatus(status: InvoiceStatus) {
    setForm((current) => {
      const chosen = current.status ?? [];
      const status_ = chosen.includes(status) ? chosen.filter((s) => s !== status) : [...chosen, status];
      return { ...current, status: status_ };
    });
  }

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const wanted = filterParams(form).toString();
    setLoading(true);
    if (wanted === query) setRefresh((n) => n + 1);
    else navigate(wanted ? `invoices?${wanted}` : "invoices");
  }

  function clear() {
    setForm({});
    if (query !== "") navigate("invoices");
  }

  async function loadMore() {
    if (next === null) return;
    setLoading(true);
    try {
      const page = await api.list({ ...parseFilters(query), pageToken: next });
      setItems((current) => [...current, ...page.items]);
      setNext(page.nextPageToken ?? null);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  const value = (name: FieldName) => form[name] ?? "";
  const field = (name: FieldName, label: string, extra: { type?: "text" | "date"; hint?: string } = {}) => (
    <TextField
      name={name}
      label={label}
      value={value(name)}
      error={problems[name]}
      onChange={change}
      {...extra}
    />
  );

  return (
    <section aria-label="All invoices" className="stack">
      <form aria-label="Search invoices" className="search-form" onSubmit={search}>
        <fieldset>
          <legend>Status</legend>
          {STATUSES.map((status) => (
            <label key={status} className="check">
              <input
                type="checkbox"
                checked={(form.status ?? []).includes(status)}
                onChange={() => toggleStatus(status)}
              />
              {STATUS_LABEL[status]}
            </label>
          ))}
        </fieldset>
        <div className="search-grid">
          {field("vendor", "Vendor", { hint: "Name or code" })}
          {field("invoiceNumber", "Invoice number")}
          {field("poNumber", "PO number", { hint: "7 digits" })}
          <label>
            Channel
            <select
              name="channel"
              value={value("channel")}
              onChange={(e) => change("channel", e.target.value)}
            >
              <option value="">Any</option>
              <option value="UPLOAD">Upload</option>
              <option value="MAIL">Mail</option>
            </select>
          </label>
          {field("invoiceDateFrom", "Invoice date from", { type: "date" })}
          {field("invoiceDateTo", "Invoice date to", { type: "date" })}
          {field("uploadedFrom", "Uploaded from", { type: "date" })}
          {field("uploadedTo", "Uploaded to", { type: "date" })}
          {field("totalMin", "Total from (USD)")}
          {field("totalMax", "Total to (USD)")}
        </div>
        <div className="toolbar">
          <button type="submit">Search</button>
          <button type="button" className="secondary" onClick={clear}>
            Clear
          </button>
        </div>
      </form>
      {error !== null && (
        <p role="alert" className="banner error">
          {error}
        </p>
      )}
      {!loading && items.length === 0 && error === null && <p className="empty">{EMPTY_TEXT}</p>}
      {items.length > 0 && (
        <table className="data">
          <thead>
            <tr>
              <th>Invoice number</th>
              <th>Vendor</th>
              <th>Invoice date</th>
              <th className="num">Total (USD)</th>
              <th>Status</th>
              <th>Channel</th>
              <th>Uploaded</th>
              <th>Exceptions</th>
              <th>Claimed by</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} data-testid="invoice-row">
                <td>
                  <a href={href(`${detailPath("invoices", item.id)}${query ? `?${query}` : ""}`)}>
                    {text(item.invoiceNumber)}
                  </a>
                </td>
                <td>{text(item.vendorName)}</td>
                <td>{text(item.invoiceDate)}</td>
                <td className="num">{decimal(item.totalAmount)}</td>
                <td>
                  <span className={`badge status ${item.status.toLowerCase()}`}>
                    {STATUS_LABEL[item.status]}
                  </span>
                </td>
                <td>{CHANNEL_LABEL[item.channel]}</td>
                <td>{timestamp(item.uploadedAt)}</td>
                <td>{(item.openExceptionCodes ?? []).join(", ") || "—"}</td>
                <td>{text(item.assignedTo?.displayName)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {loading && <p>Loading…</p>}
      {next !== null && !loading && (
        <button type="button" className="secondary" onClick={() => void loadMore()}>
          Load more
        </button>
      )}
    </section>
  );
}
