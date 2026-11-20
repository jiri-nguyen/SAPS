import { type ReactNode, useEffect, useMemo, useState } from "react";

import { type ApiHealth, fetchApiHealth } from "./api/health";
import type { ExceptionApi } from "./api/exceptions";
import type { InvoiceApi } from "./api/invoices";
import type { NotificationApi } from "./api/notifications";
import type { SettingsApi } from "./api/settings";
import { type SessionApi, createSessionApi } from "./api/session";
import { SessionProvider } from "./auth/SessionProvider";
import { SignInPage } from "./auth/SignInPage";
import { useSession } from "./auth/session-context";
import { AppShell } from "./layout/AppShell";

function HealthFooter({ checkHealth }: { checkHealth: () => Promise<ApiHealth> }) {
  const [health, setHealth] = useState<ApiHealth | "checking">("checking");

  useEffect(() => {
    let active = true;
    void checkHealth().then((result) => {
      if (active) setHealth(result);
    });
    return () => {
      active = false;
    };
  }, [checkHealth]);

  return (
    <footer>
      SAPS API: <strong data-testid="api-health">{health}</strong>
    </footer>
  );
}

function Screens({
  footer,
  invoiceApi,
  exceptionApi,
  settingsApi,
  notificationApi,
}: {
  footer: ReactNode;
  invoiceApi?: InvoiceApi;
  exceptionApi?: ExceptionApi;
  settingsApi?: SettingsApi;
  notificationApi?: NotificationApi;
}) {
  const { user } = useSession();
  if (user === undefined) return <p>Loading…</p>;
  if (user === null)
    return (
      <>
        <SignInPage />
        {footer}
      </>
    );
  return (
    <AppShell
      user={user}
      footer={footer}
      invoiceApi={invoiceApi}
      exceptionApi={exceptionApi}
      settingsApi={settingsApi}
      notificationApi={notificationApi}
    />
  );
}

export function App({
  checkHealth = fetchApiHealth,
  sessionApi,
  invoiceApi,
  exceptionApi,
  settingsApi,
  notificationApi,
}: {
  checkHealth?: () => Promise<ApiHealth>;
  sessionApi?: SessionApi;
  invoiceApi?: InvoiceApi;
  exceptionApi?: ExceptionApi;
  settingsApi?: SettingsApi;
  notificationApi?: NotificationApi;
}) {
  const api = useMemo(() => sessionApi ?? createSessionApi(), [sessionApi]);
  return (
    <SessionProvider api={api}>
      <Screens
        footer={<HealthFooter checkHealth={checkHealth} />}
        invoiceApi={invoiceApi}
        exceptionApi={exceptionApi}
        settingsApi={settingsApi}
        notificationApi={notificationApi}
      />
    </SessionProvider>
  );
}
