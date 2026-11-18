import { type ReactNode, useEffect, useMemo, useState } from "react";

import { type ApiHealth, fetchApiHealth } from "./api/health";
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

function Screens({ footer }: { footer: ReactNode }) {
  const { user } = useSession();
  if (user === undefined) return <p>Loading…</p>;
  if (user === null)
    return (
      <>
        <SignInPage />
        {footer}
      </>
    );
  return <AppShell user={user} footer={footer} />;
}

export function App({
  checkHealth = fetchApiHealth,
  sessionApi,
}: {
  checkHealth?: () => Promise<ApiHealth>;
  sessionApi?: SessionApi;
}) {
  const api = useMemo(() => sessionApi ?? createSessionApi(), [sessionApi]);
  return (
    <SessionProvider api={api}>
      <Screens footer={<HealthFooter checkHealth={checkHealth} />} />
    </SessionProvider>
  );
}
