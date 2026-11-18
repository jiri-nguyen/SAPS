import { type ReactNode, useCallback, useEffect, useMemo, useState } from "react";

import { UNAUTHORIZED, unauthorizedEvents } from "../api/client";
import type { SessionApi, UserAccount } from "../api/session";
import { SessionContext, type SessionState } from "./session-context";

export function SessionProvider({ api, children }: { api: SessionApi; children: ReactNode }) {
  const [user, setUser] = useState<UserAccount | null | undefined>(undefined);

  useEffect(() => {
    let active = true;
    api.getSession().then(
      (current) => active && setUser(current),
      () => active && setUser(null),
    );
    const onUnauthorized = () => setUser(null);
    unauthorizedEvents.addEventListener(UNAUTHORIZED, onUnauthorized);
    return () => {
      active = false;
      unauthorizedEvents.removeEventListener(UNAUTHORIZED, onUnauthorized);
    };
  }, [api]);

  const signIn = useCallback(
    async (username: string, password: string) => {
      setUser(await api.signIn(username, password));
    },
    [api],
  );

  const signOut = useCallback(async () => {
    try {
      await api.signOut();
    } catch {
      // The Web App signs out locally anyway; the server session ends by its idle timeout.
    }
    setUser(null);
  }, [api]);

  const state = useMemo<SessionState>(() => ({ user, signIn, signOut }), [user, signIn, signOut]);
  return <SessionContext value={state}>{children}</SessionContext>;
}
