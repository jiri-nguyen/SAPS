import { type FormEvent, useEffect, useState } from "react";

import type { ExceptionApi, InvoiceEvent, InvoiceUpdate, Versioned } from "../api/exceptions";
import type { UserAccount } from "../api/session";
import { canHandleExceptions } from "../auth/roles";
import { href } from "../routing";
import { errorMessage, isStale } from "./errors";
import { STATUS_LABEL, decimal, exceptionText, refusedCodes, text, timestamp } from "./format";
import { InvoiceEditForm } from "./InvoiceEditForm";

type Mode = "view" | "edit" | "reject";

export type Queue = "exceptions" | "approvals" | "review";
const QUEUE_LABEL: Record<Queue, string> = {
  exceptions: "Exception queue",
  approvals: "Approval queue",
  review: "Review queue",
};

/**
 * One invoice: file, data, exceptions, history and the actions of the user's role: a member's exception handling
 * (SAPS-20) or an Accounting Manager's approval (SAPS-22). `queue` is where the user came from.
 */
export function InvoiceDetailPage({
  api,
  invoiceId,
  user,
  queue = "exceptions",
  pollMs = 2000,
}: {
  api: ExceptionApi;
  invoiceId: string;
  user: UserAccount;
  queue?: Queue;
  pollMs?: number;
}) {
  const [loaded, setLoaded] = useState<Versioned | null>(null);
  const [events, setEvents] = useState<InvoiceEvent[]>([]);
  const [version, setVersion] = useState(0);
  const [mode, setMode] = useState<Mode>("view");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState("");

  useEffect(() => {
    let active = true;
    Promise.all([api.getVersioned(invoiceId), api.events(invoiceId)]).then(
      ([current, history]) => {
        if (!active) return;
        setLoaded(current);
        setEvents(history);
      },
      (caught: unknown) => {
        if (active) setError(errorMessage(caught));
      },
    );
    return () => {
      active = false;
    };
  }, [api, invoiceId, version]);

  const matching = loaded?.invoice.status === "MATCHING";
  useEffect(() => {
    if (!matching) return;
    const timer = setInterval(() => setVersion((n) => n + 1), pollMs); // until re-matching has finished (EC-03)
    return () => clearInterval(timer);
  }, [matching, pollMs]);

  if (loaded === null) {
    return error !== null ? (
      <p role="alert" className="banner error">
        {error}
      </p>
    ) : (
      <p>Loading…</p>
    );
  }

  const { invoice, etag } = loaded;
  const member = canHandleExceptions(user.role);
  const claimant = invoice.assignedTo?.id === user.id;
  const inException = invoice.status === "EXCEPTION";
  const manager = user.role === "ACCOUNTING_MANAGER";
  const waiting = invoice.status === "PENDING_APPROVAL"; // SAPS-22
  const reviewing = invoice.status === "PENDING_REVIEW"; // SAPS-21
  const openCodes = invoice.exceptions.filter((e) => e.status === "OPEN").map((e) => e.code);
  const refused = refusedCodes(openCodes);

  async function run(
    action: () => Promise<Versioned | undefined>,
    done: (result: Versioned | undefined) => string | null,
  ) {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      const result = await action();
      if (result) setLoaded(result);
      setNotice(done(result));
      setMode("view");
    } catch (caught) {
      if (isStale(caught)) {
        setNotice("The invoice changed since you loaded it. It has been reloaded; check it and try again.");
        setMode("view");
      } else {
        setError(errorMessage(caught));
      }
    } finally {
      setBusy(false);
      setVersion((n) => n + 1); // fresh data and history
    }
  }

  const save = (body: InvoiceUpdate) =>
    void run(
      () => api.update(invoiceId, body, etag),
      (result) =>
        result && "rematch" in result && result.rematch
          ? "Saved. Matching runs again with the corrected data."
          : "Saved.",
    );
  const confirm = () =>
    void run(
      () => api.confirm(invoiceId),
      () => "Confirmed. The invoice is completed and ready for posting.",
    );
  const approve = () =>
    void run(
      () => api.decide(invoiceId, "APPROVED"),
      (result) => (result ? `Approved. Next step: ${STATUS_LABEL[result.invoice.status]}.` : null),
    );
  const accept = () =>
    void run(
      () => api.resolve(invoiceId, etag),
      (result) => (result ? `Accepted. Next step: ${STATUS_LABEL[result.invoice.status]}.` : null),
    );
  const claim = () =>
    void run(
      () => api.claim(invoiceId),
      () => "You claimed this invoice.",
    );
  const release = () =>
    void run(
      async () => {
        await api.release(invoiceId);
        return undefined;
      },
      () => "The claim was released.",
    );
  function reject(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (reason.trim() === "") {
      setError("Enter the reason for the rejection.");
      return;
    }
    void run(
      // A manager rejects through the approval, a member in exception handling (SAPS-22 BR-05, SAPS-20 BR-08).
      () =>
        waiting ? api.decide(invoiceId, "REJECTED", reason.trim()) : api.reject(invoiceId, reason.trim()),
      () => "The invoice was rejected.",
    );
  }

  return (
    <article className="stack" aria-label="Invoice">
      <a href={href(queue)}>← {QUEUE_LABEL[queue]}</a>
      <header className="invoice-head">
        <h2>
          {text(invoice.invoiceNumber)} <span className="muted">{text(invoice.vendorName)}</span>
        </h2>
        <span className={`badge status ${invoice.status.toLowerCase()}`}>{STATUS_LABEL[invoice.status]}</span>
        <span>Total {decimal(invoice.totalAmount)} USD</span>
        {(inException || invoice.assignedTo != null) && (
          <span>Claimed by {invoice.assignedTo?.displayName ?? "nobody"}</span>
        )}
      </header>

      {matching && (
        <p className="banner info" role="status">
          Re-matching in progress…
        </p>
      )}
      {waiting && (
        <p className="banner info" role="status">
          {manager
            ? "This invoice waits for your decision."
            : "This invoice waits for approval by an Accounting Manager."}
        </p>
      )}
      {reviewing && (
        <p className="banner info" role="status">
          {member
            ? "This invoice waits for your final review: confirm or reject the result."
            : "This invoice waits for the final review by an Accounting Member."}
        </p>
      )}
      {invoice.status === "COMPLETED" && (
        <p className="banner info" role="status">
          This invoice is Completed: ready for posting.
        </p>
      )}
      {invoice.status === "REJECTED" && (
        <p className="banner info" role="status">
          This invoice is Rejected{invoice.rejectedReason ? `: ${invoice.rejectedReason}` : "."}
        </p>
      )}
      {notice !== null && (
        <p className="banner success" role="status">
          {notice}
        </p>
      )}
      {error !== null && (
        <p className="banner error" role="alert">
          {error}
        </p>
      )}

      {reviewing && member && mode === "view" && (
        <div className="actions" aria-label="Final review">
          <button type="button" className="primary" disabled={busy} onClick={confirm}>
            Confirm
          </button>
          <button type="button" className="danger" disabled={busy} onClick={() => setMode("reject")}>
            Reject
          </button>
        </div>
      )}

      {waiting && manager && mode === "view" && (
        <div className="actions" aria-label="Approval">
          <button type="button" className="primary" disabled={busy} onClick={approve}>
            Approve
          </button>
          <button type="button" className="danger" disabled={busy} onClick={() => setMode("reject")}>
            Reject
          </button>
        </div>
      )}

      {inException && mode === "view" && (
        <div className="actions" aria-label="Actions">
          {member && invoice.assignedTo == null && (
            <button type="button" className="primary" disabled={busy} onClick={claim}>
              Claim
            </button>
          )}
          {member && claimant && (
            <>
              <button type="button" className="primary" disabled={busy} onClick={() => setMode("edit")}>
                Correct data
              </button>
              <button
                type="button"
                disabled={busy || refused.length > 0}
                title={refused.length > 0 ? `${refused.join(", ")} cannot be accepted as is` : undefined}
                onClick={accept}
              >
                Accept as is
              </button>
              <button type="button" className="danger" disabled={busy} onClick={() => setMode("reject")}>
                Reject
              </button>
            </>
          )}
          {invoice.assignedTo != null && (claimant || !member) && (
            <button type="button" className="secondary" disabled={busy} onClick={release}>
              Release claim
            </button>
          )}
          {member && claimant && refused.length > 0 && (
            <p className="hint">
              {refused.join(", ")} cannot be accepted as is: correct the data or reject the invoice.
            </p>
          )}
        </div>
      )}

      {mode === "edit" && (
        <InvoiceEditForm invoice={invoice} busy={busy} onSave={save} onCancel={() => setMode("view")} />
      )}
      {mode === "reject" && (
        <form className="stack" aria-label="Reject invoice" onSubmit={reject}>
          <label>
            Reason
            <textarea maxLength={1000} value={reason} onChange={(e) => setReason(e.target.value)} />
          </label>
          <div className="actions">
            <button type="submit" className="danger" disabled={busy}>
              Reject invoice
            </button>
            <button type="button" className="secondary" onClick={() => setMode("view")}>
              Cancel
            </button>
          </div>
        </form>
      )}

      <div className="split">
        <section className="viewer" aria-label="Invoice file">
          {invoice.file.contentType === "application/pdf" ? (
            <iframe title="Invoice file" src={api.fileUrl(invoiceId)} />
          ) : (
            <img alt="Invoice file" src={api.fileUrl(invoiceId)} />
          )}
        </section>
        <section className="stack">
          <dl className="facts">
            <dt>Vendor</dt>
            <dd>
              {text(invoice.vendorName)} ({text(invoice.vendorCode)})
            </dd>
            <dt>Invoice date</dt>
            <dd>{text(invoice.invoiceDate)}</dd>
            <dt>Invoice type</dt>
            <dd>{text(invoice.invoiceType)}</dd>
            <dt>Subtotal / tax / total</dt>
            <dd>
              {decimal(invoice.subtotalAmount)} / {decimal(invoice.taxAmount)} /{" "}
              {decimal(invoice.totalAmount)} USD
            </dd>
            <dt>File</dt>
            <dd>{invoice.file.name}</dd>
            {invoice.approval != null && (
              <>
                <dt>Approval</dt>
                <dd>
                  {invoice.approval.decision === "APPROVED" ? "Approved" : "Rejected"} by{" "}
                  {invoice.approval.decidedBy.displayName} on {timestamp(invoice.approval.decidedAt)}
                  {invoice.approval.comment ? `: ${invoice.approval.comment}` : ""}
                </dd>
              </>
            )}
          </dl>

          <h3>Exceptions</h3>
          <ul className="exceptions">
            {invoice.exceptions.map((exception) => (
              <li key={exception.id} className={exception.status === "OPEN" ? "open" : "resolved"}>
                <span className="badge code">{exception.code}</span>{" "}
                {exceptionText(exception.code, exception.message)}
                {exception.status === "RESOLVED" && (
                  <span className="muted">
                    {" "}
                    (resolved{exception.resolvedBy ? ` by ${exception.resolvedBy.displayName}` : ""}
                    {exception.resolvedAt ? ` on ${timestamp(exception.resolvedAt)}` : ""})
                  </span>
                )}
              </li>
            ))}
          </ul>

          <h3>Lines</h3>
          <table className="data">
            <thead>
              <tr>
                <th>Line</th>
                <th>Description</th>
                <th>PO</th>
                <th className="num">Quantity</th>
                <th className="num">Unit price</th>
                <th className="num">PO unit price</th>
                <th className="num">Expected quantity</th>
                <th>Match</th>
              </tr>
            </thead>
            <tbody>
              {invoice.lines.map((line) => (
                <tr key={line.id}>
                  <td>{line.lineNumber}</td>
                  <td>{text(line.description)}</td>
                  <td>
                    {text(line.poNumber)}
                    {line.poLineNumber != null ? ` / ${line.poLineNumber}` : ""}
                  </td>
                  <td className="num">{decimal(line.quantity, 0)}</td>
                  <td className="num">{decimal(line.unitPrice)}</td>
                  <td className="num">{decimal(line.poUnitPrice)}</td>
                  <td className="num">{decimal(line.expectedQuantity, 0)}</td>
                  <td>{line.matchStatus.replace("_", " ").toLowerCase()}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <h3>History</h3>
          <ol className="history">
            {events.map((event) => (
              <li key={event.id}>
                {timestamp(event.occurredAt)} · {event.action} · {event.actor} ·{" "}
                {STATUS_LABEL[event.statusTo]}
              </li>
            ))}
          </ol>
        </section>
      </div>
    </article>
  );
}
