import { apiFetch } from "./client";
import type { components } from "./schema";

export type NotificationItem = components["schemas"]["Notification"];
export type NotificationPage = components["schemas"]["NotificationPage"];
export type NotificationType = components["schemas"]["NotificationType"];

export interface NotificationQuery {
  unreadOnly?: boolean;
  pageSize?: number;
  pageToken?: string;
}

/** Notification operations of the SAPS API (SAPS-24): the caller's own notifications. */
export interface NotificationApi {
  /** `listNotifications`, newest first, with the caller's `unreadCount`. */
  list(query?: NotificationQuery): Promise<NotificationPage>;
  /** `markNotificationRead` (idempotent). */
  markRead(notificationId: string): Promise<void>;
  /** `markAllNotificationsRead` (idempotent). */
  markAllRead(): Promise<void>;
}

export function createNotificationApi(fetchImpl: typeof fetch = fetch): NotificationApi {
  const call = (url: string, init: RequestInit = {}) => apiFetch(url, init, fetchImpl);
  return {
    async list(query = {}) {
      const params = new URLSearchParams();
      if (query.unreadOnly) params.set("unreadOnly", "true");
      if (query.pageSize) params.set("pageSize", String(query.pageSize));
      if (query.pageToken) params.set("pageToken", query.pageToken);
      const response = await call(`/v1/notifications?${params.toString()}`);
      return (await response.json()) as NotificationPage;
    },
    async markRead(notificationId) {
      await call(`/v1/notifications/${encodeURIComponent(notificationId)}/read`, { method: "POST" });
    },
    async markAllRead() {
      await call("/v1/notifications/read-all", { method: "POST" });
    },
  };
}
