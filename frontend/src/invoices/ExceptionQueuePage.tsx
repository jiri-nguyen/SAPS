import { useEffect, useState } from "react";

import type { ExceptionApi, InvoiceSummary } from "../api/exceptions";
import type { Role } from "../api/session";
import { canHandleExceptions } from "../auth/roles";
import { href, invoicePath, navigate } from "../routing";
import { errorMessage } from "./errors";
import { EXCEPTION_TITLE, decimal, text, timestamp } from "./format";

type Tab = "unassigned" | "me";

const TABS: readonly { id: Tab; label: string }[] = [
  { id: "unassigned", label: "Unclaimed" },
  { id: "me", label: "Mine" },
];

/** The shared exception queue (SAPS-20 BR-01); read-only for Accounting Managers. */
export function ExceptionQueuePage({ api, role }: { api: ExceptionApi; role: Role }) {
  const member = canHandleExceptions(role);
  const [tab, setTab] = useState<Tab>("unassigned");
  const [refresh, setRefresh] = useState(0);
  const [items, setItems] = useState<InvoiceSummary[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const assignee = member ? tab : undefined;

  useEffect(() => {
    let active = true;
    api.list({ status: ["EXCEPTION"], assignee }).then(
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
  }, [api, assignee, refresh]);

  function reload(nextTab: Tab = tab) {
    setTab(nextTab);
    setLoading(true);
    setError(null);
    setRefresh((n) => n + 1);
  }

  async function loadMore() {
    if (next === null) return;
    setLoading(true);
    try {
      const page = await api.list({ status: ["EXCEPTION"], assignee, pageToken: next });
      setItems((current) => [...current, ...page.items]);
      setNext(page.nextPageToken ?? null);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  async function claim(invoiceId: string) {
    setError(null);
    try {
      await api.claim(invoiceId);
      navigate(invoicePath(invoiceId));
    } catch (caught) {
      reload();
      setError(errorMessage(caught)); // after reload(), which clears it: e.g. claimed by another member (409)
    }
  }

  return (
    <section aria-label="Exception queue" className="stack">
      <div className="toolbar">
        {member && (
          <div role="tablist" aria-label="Queue">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={tab === t.id}
                className={tab === t.id ? "tab active" : "tab"}
                onClick={() => reload(t.id)}
              >
                {t.label}
              </button>
            ))}
          </div>
        )}
        {!member && <p className="hint">Read only. You can release a claim from the invoice.</p>}
        <button type="button" className="secondary" onClick={() => reload()}>
          Refresh
        </button>
      </div>
      {error !== null && (
        <p role="alert" className="banner error">
          {error}
        </p>
      )}
      {!loading && items.length === 0 && error === null && (
        <p className="empty">No invoices in this queue.</p>
      )}
      {items.length > 0 && (
        <table className="data">
          <thead>
            <tr>
              <th>Vendor</th>
              <th>Invoice number</th>
              <th className="num">Total (USD)</th>
              <th>Open exceptions</th>
              <th>Claimed by</th>
              <th>Updated</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id} data-testid="queue-row">
                <td>{text(item.vendorName)}</td>
                <td>
                  <a href={href(invoicePath(item.id))}>{text(item.invoiceNumber)}</a>
                </td>
                <td className="num">{decimal(item.totalAmount)}</td>
                <td>
                  {(item.openExceptionCodes ?? []).map((code) => (
                    <span key={code} className="badge code" title={EXCEPTION_TITLE[code]}>
                      {code}
                    </span>
                  ))}
                </td>
                <td>{item.assignedTo?.displayName ?? "—"}</td>
                <td>{timestamp(item.updatedAt)}</td>
                <td>
                  {member && item.assignedTo == null && (
                    <button type="button" onClick={() => void claim(item.id)}>
                      Claim
                    </button>
                  )}
                </td>
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
