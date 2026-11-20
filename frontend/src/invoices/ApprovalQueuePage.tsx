import { useEffect, useState } from "react";

import type { ExceptionApi, InvoiceSummary } from "../api/exceptions";
import { detailPath, href } from "../routing";
import { errorMessage } from "./errors";
import { decimal, text, timestamp } from "./format";

/** Invoices above the approval threshold, waiting for an Accounting Manager (SAPS-22). One shared queue (DEC-038). */
export function ApprovalQueuePage({ api }: { api: ExceptionApi }) {
  const [refresh, setRefresh] = useState(0);
  const [items, setItems] = useState<InvoiceSummary[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    api.list({ status: ["PENDING_APPROVAL"] }).then(
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
  }, [api, refresh]);

  async function loadMore() {
    if (next === null) return;
    setLoading(true);
    try {
      const page = await api.list({ status: ["PENDING_APPROVAL"], pageToken: next });
      setItems((current) => [...current, ...page.items]);
      setNext(page.nextPageToken ?? null);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section aria-label="Approval queue" className="stack">
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
      {!loading && items.length === 0 && error === null && (
        <p className="empty">No invoices wait for approval.</p>
      )}
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
              <tr key={item.id} data-testid="approval-row">
                <td>{text(item.vendorName)}</td>
                <td>
                  <a href={href(detailPath("approvals", item.id))}>{text(item.invoiceNumber)}</a>
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
