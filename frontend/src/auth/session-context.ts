import { createContext, useContext } from "react";

import type { UserAccount } from "../api/session";

export interface SessionState {
  /** `undefined` while the current session is being read. */
  user: UserAccount | null | undefined;
  /** Ends the SAPS session, then sends the browser to the Identity Provider to end that session too. */
  signOut(): Promise<void>;
}

export const SessionContext = createContext<SessionState | null>(null);

export function useSession(): SessionState {
  const state = useContext(SessionContext);
  if (state === null) throw new Error("useSession must be used inside SessionProvider");
  return state;
}
