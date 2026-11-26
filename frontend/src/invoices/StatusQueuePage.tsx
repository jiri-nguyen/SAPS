import { useEffect, useState } from "react";

import type { ExceptionApi, InvoiceSummary } from "../api/exceptions";
import type { InvoiceStatus } from "../api/invoices";
import { detailPath, href } from "../routing";
import { errorMessage } from "./errors";
import { decimal, text, timestamp } from "./format";

/**
 * A shared queue of invoices in one status, without claims: the approval queue (Pending approval, Accounting Managers,
 * SAPS-22, DEC-038). The final review queue of SAPS-21 was removed with DEC-063.
 */
export function StatusQueuePage({
  api,
  status,
  queue,
  label,
  emptyText,
}: {
  api: ExceptionApi;
  status: InvoiceStatus;
  queue: string;
  label: string;
  emptyText: string;
}) {
  const [refresh, setRefresh] = useState(0);
  const [items, setItems] = useState<InvoiceSummary[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.list({ status: [status] }).then(
      (page) => {
        if (!active) return;
        setItems(page.items);
        setNext(page.nextPageToken ?? null);
        setLoading(false);
      },
      (caught: unknown) => {
        if (!active) return;
        setError(errorMessage(caught));
        setLoading(false);
      },
    );
    return () => {
      active = false;
    };
  }, [api, status, refresh]);

  async function loadMore() {
    if (next === null) return;
    setLoading(true);
    try {
      const page = await api.list({ status: [status], pageToken: next });
      setItems((current) => [...current, ...page.items]);
      setNext(page.nextPageToken ?? null);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section aria-label={label} className="stack">
      <div className="toolbar">
        <button
          type="button"
          className="secondary"
          onClick={() => {
            setLoading(true);
            setError(null);
            setRefresh((n) => n + 1);
          }}
        >
          Refresh
        </button>
      </div>
      {error !== null && (
        <p role="alert" className="banner error">
          {error}
        </p>
      )}
      {!loading && items.length === 0 && error === null && <p className="empty">{emptyText}</p>}
      {items.length > 0 && (
        <table className="data">
          <thead>
            <tr>
              <th>Vendor</th>
              <th>Invoice number</th>
              <th className="num">Total (USD)</th>
              <th>Type</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} data-testid="status-row">
                <td>{text(item.vendorName)}</td>
                <td>
                  <a href={href(detailPath(queue, item.id))}>{text(item.invoiceNumber)}</a>
                </td>
                <td className="num">{decimal(item.totalAmount)}</td>
                <td>{text(item.invoiceType)}</td>
                <td>{timestamp(item.updatedAt)}</td>
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
