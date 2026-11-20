import { vi } from "vitest";

import type { NotificationApi, NotificationItem, NotificationPage } from "../api/notifications";

export function notificationFixture(overrides: Partial<NotificationItem> = {}): NotificationItem {
  return {
    id: "n-1",
    type: "EXCEPTION_RAISED",
    invoiceId: "inv-12",
    message: "Invoice AOS-2026-1013 from Alpha Office Supplies Co. has exceptions: EX6.",
    readAt: null,
    createdAt: "2026-12-15T09:30:00Z",
    ...overrides,
  };
}

export function notificationPage(
  items: NotificationItem[],
  unreadCount = items.filter((item) => !item.readAt).length,
  nextPageToken: string | null = null,
): NotificationPage {
  return { items, nextPageToken, unreadCount };
}

export function fakeNotificationApi(overrides: Partial<NotificationApi> = {}): NotificationApi {
  return {
    list: vi.fn().mockResolvedValue(notificationPage([])),
    markRead: vi.fn().mockResolvedValue(undefined),
    markAllRead: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}
