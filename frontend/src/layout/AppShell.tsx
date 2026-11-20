import { type ReactNode, useMemo } from "react";

import { type ExceptionApi, createExceptionApi } from "../api/exceptions";
import { type InvoiceApi, createInvoiceApi } from "../api/invoices";
import type { UserAccount } from "../api/session";
import { MENU_BY_ROLE, ROLE_LABEL } from "../auth/roles";
import { useSession } from "../auth/session-context";
import { ExceptionQueuePage } from "../invoices/ExceptionQueuePage";
import { InvoiceDetailPage } from "../invoices/InvoiceDetailPage";
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
  const canOpenInvoices = menu.some((item) => item.id === "exceptions");
  const detail = route.page === "invoice" && route.invoiceId !== undefined && canOpenInvoices;
  const pageId = detail ? "exceptions" : route.page;
  // A route the role may not open (or none) shows the role's first screen (SAPS-27 BR-10).
  const current = menu.find((item) => item.id === pageId) ?? menu[0];

  let page: ReactNode;
  if (detail) {
    page = (
      <InvoiceDetailPage
        key={route.invoiceId}
        api={exceptions}
        invoiceId={route.invoiceId ?? ""}
        user={user}
      />
    );
  } else if (current.id === "upload") {
    page = <UploadPage api={invoices} />;
  } else if (current.id === "exceptions") {
    page = <ExceptionQueuePage api={exceptions} role={user.role} />;
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
