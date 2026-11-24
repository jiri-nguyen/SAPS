import { ApiError, apiFetch } from "./client";
import type { components } from "./schema";

export type UserAccount = components["schemas"]["UserAccount"];
export type Role = components["schemas"]["Role"];

export interface SessionApi {
  getSession(): Promise<UserAccount | null>;
  /** Returns where the browser goes next to end the Identity Provider session (SAPS-44). */
  signOut(): Promise<string>;
}

/** `getSession` and `deleteSession` of the SAPS API; sign-in is a browser redirect (SAPS-44). */
export function createSessionApi(fetchImpl: typeof fetch = fetch): SessionApi {
  return {
    async getSession() {
      try {
        const response = await apiFetch("/v1/session", {}, fetchImpl);
        return (await response.json()) as UserAccount;
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) return null;
        throw error;
      }
    },
    async signOut() {
      const response = await apiFetch("/v1/session", { method: "DELETE" }, fetchImpl);
      const body = (await response.json()) as components["schemas"]["SignOut"];
      return body.logoutUrl;
    },
  };
}
