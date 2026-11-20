import { useCallback, useEffect, useRef, useState } from "react";

import type { NotificationApi, NotificationItem, NotificationType } from "../api/notifications";
import { errorMessage } from "../invoices/errors";
import { timestamp } from "../invoices/format";
import { detailPath, navigate } from "../routing";
import { pollIntervalMs } from "./config";

const PAGE_SIZE = 20;

/** The screen that shows the invoice of a notification, by type (SAPS-24 BR-05: it shows the current status). */
const QUEUE_OF: Record<NotificationType, string> = {
  EXCEPTION_RAISED: "exceptions",
  APPROVAL_REQUESTED: "approvals",
  REVIEW_REQUESTED: "review",
};

/**
 * The bell of the top bar (SAPS-24 BR-06): polls the unread count, opens a panel with the latest notifications,
 * opens the invoice of a clicked notification and marks it read, and marks everything read.
 */
export function NotificationBell({
  api,
  pollMs = pollIntervalMs(),
}: {
  api: NotificationApi;
  pollMs?: number;
}) {
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [next, setNext] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const root = useRef<HTMLDivElement>(null);
  const bell = useRef<HTMLButtonElement>(null);

  // A failed poll keeps the last count; an expired session is handled by the sign-in page (EC-06).
  const readCount = useCallback(
    () =>
      api.list({ unreadOnly: true, pageSize: 1 }).then(
        (page) => page.unreadCount,
        () => null,
      ),
    [api],
  );

  useEffect(() => {
    let active = true;
    const poll = () =>
      void readCount().then((count) => {
        if (active && count !== null) setUnread(count);
      });
    poll();
    const timer = setInterval(poll, pollMs);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [readCount, pollMs]);

  // The panel shows the first page whenever it opens and whenever the unread count changes while it is open.
  useEffect(() => {
    if (!open) return;
    let active = true;
    api.list({ pageSize: PAGE_SIZE }).then(
      (page) => {
        if (!active) return;
        setItems(page.items);
        setNext(page.nextPageToken ?? null);
        setError(null);
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
  }, [api, open, unread]);

  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      setOpen(false);
      bell.current?.focus();
    };
    const onPointer = (event: MouseEvent) => {
      if (root.current && !root.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("keydown", onKey);
    document.addEventListener("mousedown", onPointer);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.removeEventListener("mousedown", onPointer);
    };
  }, [open]);

  function toggle() {
    if (!open) setLoading(true); // the first page is read by the effect below
    setOpen(!open);
  }

  async function loadMore() {
    if (next === null) return;
    setLoading(true);
    try {
      const page = await api.list({ pageSize: PAGE_SIZE, pageToken: next });
      setItems((current) => [...current, ...page.items]);
      setNext(page.nextPageToken ?? null);
    } catch (caught) {
      setError(errorMessage(caught));
    } finally {
      setLoading(false);
    }
  }

  async function markAllRead() {
    setError(null);
    try {
      await api.markAllRead();
      setUnread(0);
    } catch (caught) {
      setError(errorMessage(caught));
    }
  }

  async function choose(item: NotificationItem) {
    setOpen(false);
    navigate(detailPath(QUEUE_OF[item.type], item.invoiceId));
    if (item.readAt) return;
    try {
      await api.markRead(item.id);
    } catch {
      // Not marking it read must not block the user from the invoice.
    }
    const count = await readCount();
    if (count !== null) setUnread(count);
  }

  return (
    <div className="bell" ref={root}>
      <button
        type="button"
        ref={bell}
        className="bell-button"
        aria-label={unread > 0 ? `Notifications, ${unread} unread` : "Notifications"}
        aria-expanded={open}
        aria-controls="notification-panel"
        onClick={toggle}
      >
        <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
          <path
            fill="currentColor"
            d="M12 22a2.5 2.5 0 0 0 2.4-1.8h-4.8A2.5 2.5 0 0 0 12 22Zm7-5.5V11a7 7 0 0 0-5.5-6.8V3.5a1.5 1.5 0 0 0-3 0v.7A7 7 0 0 0 5 11v5.5l-1.7 1.7V19h17.4v-.8L19 16.5Z"
          />
        </svg>
        {unread > 0 && (
          <span className="badge-count" aria-hidden="true">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>
      {open && (
        <div id="notification-panel" className="notification-panel" role="dialog" aria-label="Notifications">
          <div className="notification-head">
            <strong>Notifications</strong>
            <button
              type="button"
              className="secondary"
              disabled={unread === 0}
              onClick={() => void markAllRead()}
            >
              Mark all as read
            </button>
          </div>
          {error !== null && (
            <p role="alert" className="banner error">
              {error}
            </p>
          )}
          {items.length === 0 && !loading && error === null && <p className="muted">No notifications.</p>}
          <ul className="notification-list">
            {items.map((item) => (
              <li key={item.id}>
                <button
                  type="button"
                  className={item.readAt ? "notification read" : "notification unread"}
                  onClick={() => void choose(item)}
                >
                  <span>{item.message}</span>
                  <span className="muted">
                    {timestamp(item.createdAt)}
                    {item.readAt ? "" : " · unread"}
                  </span>
                </button>
              </li>
            ))}
          </ul>
          {loading && <p className="muted">Loading…</p>}
          {next !== null && !loading && (
            <button type="button" className="secondary" onClick={() => void loadMore()}>
              Load more
            </button>
          )}
        </div>
      )}
    </div>
  );
}
