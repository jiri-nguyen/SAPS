import { ApiError, apiFetch } from "./client";
import type { components } from "./schema";

export type UserAccount = components["schemas"]["UserAccount"];
export type Role = components["schemas"]["Role"];

export interface SessionApi {
  getSession(): Promise<UserAccount | null>;
  signIn(username: string, password: string): Promise<UserAccount>;
  signOut(): Promise<void>;
}

/** `getSession`, `createSession`, `deleteSession` of the SAPS API (SAPS-27). */
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
    async signIn(username, password) {
      const body: components["schemas"]["SessionCreate"] = { username, password };
      const response = await apiFetch(
        "/v1/session",
        { method: "POST", body: JSON.stringify(body) },
        fetchImpl,
      );
      return (await response.json()) as UserAccount;
    },
    async signOut() {
      await apiFetch("/v1/session", { method: "DELETE" }, fetchImpl);
    },
  };
}
