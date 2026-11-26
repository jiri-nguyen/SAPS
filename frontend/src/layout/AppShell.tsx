import { type ReactNode, useMemo, useState } from "react";

import { type CalendarApi, createCalendarApi } from "../api/calendar";
import { type ExceptionApi, createExceptionApi } from "../api/exceptions";
import { type InvoiceApi, createInvoiceApi } from "../api/invoices";
import { type NotificationApi, createNotificationApi } from "../api/notifications";
import { type SettingsApi, createSettingsApi } from "../api/settings";
import type { UserAccount } from "../api/session";
import { MENU_BY_ROLE, ROLE_LABEL } from "../auth/roles";
import { useSession } from "../auth/session-context";
import { ExceptionQueuePage } from "../invoices/ExceptionQueuePage";
import { InvoiceDetailPage, type Queue } from "../invoices/InvoiceDetailPage";
import { InvoiceSearchPage } from "../invoices/InvoiceSearchPage";
import { StatusQueuePage } from "../invoices/StatusQueuePage";
import { UploadPage } from "../invoices/UploadPage";
import { NotificationBell } from "../notifications/NotificationBell";
import { href, useRoute } from "../routing";
import { MatchingSettingsPage } from "../settings/MatchingSettingsPage";
import { ProcessingCalendarPage } from "../settings/ProcessingCalendarPage";
import { CalendarBanner } from "./CalendarBanner";

export function AppShell({
  user,
  footer,
  invoiceApi,
  exceptionApi,
  settingsApi,
  notificationApi,
  calendarApi,
}: {
  user: UserAccount;
  footer?: ReactNode;
  invoiceApi?: InvoiceApi;
  exceptionApi?: ExceptionApi;
  settingsApi?: SettingsApi;
  notificationApi?: NotificationApi;
  calendarApi?: CalendarApi;
}) {
  const { signOut } = useSession();
  const invoices = useMemo(() => invoiceApi ?? createInvoiceApi(), [invoiceApi]);
  const exceptions = useMemo(() => exceptionApi ?? createExceptionApi(), [exceptionApi]);
  const settings = useMemo(() => settingsApi ?? createSettingsApi(), [settingsApi]);
  const notifications = useMemo(() => notificationApi ?? createNotificationApi(), [notificationApi]);
  const calendar = useMemo(() => calendarApi ?? createCalendarApi(), [calendarApi]);
  const [calendarVersion, setCalendarVersion] = useState(0); // the banner reads the calendar again after a change
  const menu = MENU_BY_ROLE[user.role];
  const route = useRoute();
  // A route the role may not open (or none) shows the role's first screen (SAPS-27 BR-10).
  const current = menu.find((item) => item.id === route.page) ?? menu[0];
  const queue: Queue | null =
    current.id === "exceptions" || current.id === "approvals" || current.id === "invoices"
      ? current.id
      : null;
  const invoiceId = route.page === current.id ? route.invoiceId : undefined;
  const detail = queue !== null && invoiceId !== undefined;

  let page: ReactNode;
  if (detail) {
    page = (
      <InvoiceDetailPage
        key={invoiceId}
        api={exceptions}
        invoiceId={invoiceId}
        user={user}
        queue={queue}
        backQuery={route.query}
      />
    );
  } else if (current.id === "upload") {
    page = <UploadPage api={invoices} />;
  } else if (current.id === "invoices") {
    page = <InvoiceSearchPage key={route.query ?? ""} api={exceptions} query={route.query ?? ""} />;
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
  } else if (current.id === "processing-calendar") {
    page = <ProcessingCalendarPage api={calendar} onChanged={() => setCalendarVersion((n) => n + 1)} />;
  } else {
    page = <MatchingSettingsPage api={settings} />;
  }

  return (
    <div className="shell">
      <header className="topbar">
        <strong>Smart-AP-Suite</strong>
        <NotificationBell api={notifications} />
        <span data-testid="signed-in-user">
          {user.displayName} ({ROLE_LABEL[user.role]}){user.companyName ? ` · ${user.companyName}` : ""}
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
        <CalendarBanner
          api={calendar}
          company={user.companyName}
          refreshKey={`${route.page}/${calendarVersion}`}
        />
        <h1>{detail ? "Invoice" : current.label}</h1>
        {page}
      </main>
      {footer}
    </div>
  );
}
