import { type ReactNode, useMemo } from "react";

import { type ExceptionApi, createExceptionApi } from "../api/exceptions";
import { type InvoiceApi, createInvoiceApi } from "../api/invoices";
import type { UserAccount } from "../api/session";
import { MENU_BY_ROLE, ROLE_LABEL } from "../auth/roles";
import { useSession } from "../auth/session-context";
import { ExceptionQueuePage } from "../invoices/ExceptionQueuePage";
import { InvoiceDetailPage, type Queue } from "../invoices/InvoiceDetailPage";
import { StatusQueuePage } from "../invoices/StatusQueuePage";
import { UploadPage } from "../invoices/UploadPage";
import { href, useRoute } from "../routing";

export function AppShell({
  user,
  footer,
  invoiceApi,
  exceptionApi,
}: {
  user: UserAccount;
  footer?: ReactNode;
  invoiceApi?: InvoiceApi;
  exceptionApi?: ExceptionApi;
}) {
  const { signOut } = useSession();
  const invoices = useMemo(() => invoiceApi ?? createInvoiceApi(), [invoiceApi]);
  const exceptions = useMemo(() => exceptionApi ?? createExceptionApi(), [exceptionApi]);
  const menu = MENU_BY_ROLE[user.role];
  const route = useRoute();
  // A route the role may not open (or none) shows the role's first screen (SAPS-27 BR-10).
  const current = menu.find((item) => item.id === route.page) ?? menu[0];
  const queue: Queue | null =
    current.id === "exceptions" || current.id === "approvals" || current.id === "review" ? current.id : null;
  const invoiceId = route.page === current.id ? route.invoiceId : undefined;
  const detail = queue !== null && invoiceId !== undefined;

  let page: ReactNode;
  if (detail) {
    page = (
      <InvoiceDetailPage key={invoiceId} api={exceptions} invoiceId={invoiceId} user={user} queue={queue} />
    );
  } else if (current.id === "upload") {
    page = <UploadPage api={invoices} />;
  } else if (current.id === "exceptions") {
    page = <ExceptionQueuePage api={exceptions} role={user.role} />;
  } else if (current.id === "approvals") {
    page = (
      <StatusQueuePage
        api={exceptions}
        status="PENDING_APPROVAL"
        queue="approvals"
        label="Approval queue"
        emptyText="No invoices wait for approval."
      />
    );
  } else if (current.id === "review") {
    page = (
      <StatusQueuePage
        api={exceptions}
        status="PENDING_REVIEW"
        queue="review"
        label="Review queue"
        emptyText="No invoices wait for the final review."
      />
    );
  } else {
    page = <p>This screen is not available yet.</p>;
  }

  return (
    <div className="shell">
      <header className="topbar">
        <strong>Smart-AP-Suite</strong>
        <span data-testid="signed-in-user">
          {user.displayName} ({ROLE_LABEL[user.role]})
        </span>
        <button type="button" className="secondary" onClick={() => void signOut()}>
          Sign out
        </button>
      </header>
      <nav aria-label="Main menu" className="menu">
        <ul>
          {menu.map((item) => (
            <li key={item.id}>
              <a href={href(item.id)} aria-current={item.id === current.id ? "page" : undefined}>
                {item.label}
              </a>
            </li>
          ))}
        </ul>
      </nav>
      <main className="content">
        <h1>{detail ? "Invoice" : current.label}</h1>
        {page}
      </main>
      {footer}
    </div>
  );
}
