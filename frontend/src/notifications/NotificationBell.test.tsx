import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { fakeNotificationApi, notificationFixture as note, notificationPage } from "../test/notifications";
import { NotificationBell } from "./NotificationBell";

const SLOW = 60_000; // no second poll during a test unless it asks for one
const bell = (name: string | RegExp = /^Notifications/) => screen.getByRole("button", { name });
const problem = (status: number, detail: string) =>
  new ApiError(status, { type: "about:blank", title: "x", status, detail });

describe("notification bell (SAPS-24 BR-06)", () => {
  it("shows no badge without unread notifications", async () => {
    const api = fakeNotificationApi();
    render(<NotificationBell api={api} pollMs={SLOW} />);
    await waitFor(() => expect(api.list).toHaveBeenCalledWith({ unreadOnly: true, pageSize: 1 }));
    expect(bell("Notifications")).toBeInTheDocument();
    expect(document.querySelector(".badge-count")).toBeNull();
  });

  it("shows the unread count, capped at 99+", async () => {
    const list = vi.fn().mockResolvedValue(notificationPage([], 3));
    const { unmount } = render(<NotificationBell api={fakeNotificationApi({ list })} pollMs={SLOW} />);
    expect(await screen.findByRole("button", { name: "Notifications, 3 unread" })).toHaveTextContent("3");
    unmount();
    list.mockResolvedValue(notificationPage([], 240));
    render(<NotificationBell api={fakeNotificationApi({ list })} pollMs={SLOW} />);
    expect(await screen.findByRole("button", { name: "Notifications, 240 unread" })).toHaveTextContent("99+");
  });

  it("polls: the count follows the server and a failed poll keeps the last count", async () => {
    const list = vi
      .fn()
      .mockResolvedValueOnce(notificationPage([], 1))
      .mockResolvedValueOnce(notificationPage([], 4))
      .mockRejectedValueOnce(new Error("network down"))
      .mockResolvedValue(notificationPage([], 4));
    render(<NotificationBell api={fakeNotificationApi({ list })} pollMs={30} />);
    expect(await screen.findByRole("button", { name: "Notifications, 1 unread" })).toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Notifications, 4 unread" })).toBeInTheDocument();
    await waitFor(() => expect(list.mock.calls.length).toBeGreaterThanOrEqual(4));
    expect(bell()).toHaveAccessibleName("Notifications, 4 unread");
  });

  it("stops polling when it is removed (sign-out)", async () => {
    const api = fakeNotificationApi();
    const { unmount } = render(<NotificationBell api={api} pollMs={20} />);
    await waitFor(() => expect(vi.mocked(api.list).mock.calls.length).toBeGreaterThanOrEqual(2));
    unmount();
    const calls = vi.mocked(api.list).mock.calls.length;
    await new Promise((resolve) => setTimeout(resolve, 80));
    expect(api.list).toHaveBeenCalledTimes(calls);
  });

  it("opens a panel with the latest notifications, unread ones marked", async () => {
    const list = vi.fn().mockImplementation(({ pageSize }: { pageSize?: number }) =>
      Promise.resolve(
        pageSize === 1
          ? notificationPage([], 1)
          : notificationPage([
              note(),
              note({
                id: "n-2",
                type: "REVIEW_REQUESTED",
                message: "Invoice X is ready.",
                readAt: "2026-12-15T10:00:00Z",
              }),
            ]),
      ),
    );
    render(<NotificationBell api={fakeNotificationApi({ list })} pollMs={SLOW} />);
    await userEvent.setup().click(bell());
    const panel = await screen.findByRole("dialog", { name: "Notifications" });
    expect(bell()).toHaveAttribute("aria-expanded", "true");
    expect(within(panel).getByText(/has exceptions: EX6/)).toBeInTheDocument();
    expect(within(panel).getByText("2026-12-15 09:30 UTC · unread")).toBeInTheDocument();
    expect(within(panel).getByText("2026-12-15 09:30 UTC · unread").closest("button")).toHaveClass("unread");
    expect(within(panel).getByText("Invoice X is ready.").closest("button")).toHaveClass("read");
    expect(within(panel).queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
    expect(list).toHaveBeenCalledWith({ pageSize: 20 });
  });

  it("says when there are no notifications", async () => {
    render(<NotificationBell api={fakeNotificationApi()} pollMs={SLOW} />);
    const user = userEvent.setup();
    await user.click(bell());
    expect(await screen.findByText("No notifications.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mark all as read" })).toBeDisabled();
    await user.click(bell());
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it.each([
    ["EXCEPTION_RAISED", "#/exceptions/inv-12"],
    ["APPROVAL_REQUESTED", "#/approvals/inv-12"],
    ["REVIEW_REQUESTED", "#/review/inv-12"],
  ] as const)("opens the invoice of a %s notification and marks it read", async (type, hash) => {
    const list = vi
      .fn()
      .mockResolvedValueOnce(notificationPage([], 1))
      .mockResolvedValueOnce(notificationPage([note({ type, message: "Open me." })], 1))
      .mockResolvedValue(notificationPage([], 0));
    const api = fakeNotificationApi({ list });
    render(<NotificationBell api={api} pollMs={SLOW} />);
    const user = userEvent.setup();
    await user.click(bell());
    await user.click(await screen.findByText("Open me."));
    expect(window.location.hash).toBe(hash);
    expect(api.markRead).toHaveBeenCalledWith("n-1");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(await screen.findByRole("button", { name: "Notifications" })).toBeInTheDocument(); // count refreshed to 0
  });

  it("does not mark a read notification again, and opens the invoice even if marking fails", async () => {
    const list = vi
      .fn()
      .mockResolvedValue(
        notificationPage([note({ readAt: "2026-12-15T10:00:00Z", message: "Old one." })], 0),
      );
    const api = fakeNotificationApi({ list, markRead: vi.fn().mockRejectedValue(problem(500, "boom")) });
    render(<NotificationBell api={api} pollMs={SLOW} />);
    const user = userEvent.setup();
    await user.click(bell());
    await user.click(await screen.findByText("Old one."));
    expect(api.markRead).not.toHaveBeenCalled();
    expect(window.location.hash).toBe("#/exceptions/inv-12");

    list.mockResolvedValue(notificationPage([note({ id: "n-9", message: "New one." })], 1));
    await user.click(bell());
    await user.click(await screen.findByText("New one."));
    expect(api.markRead).toHaveBeenCalledWith("n-9");
    expect(window.location.hash).toBe("#/exceptions/inv-12");
  });

  it("marks everything read and clears the badge", async () => {
    const list = vi
      .fn()
      .mockImplementation(({ pageSize }: { pageSize?: number }) =>
        Promise.resolve(notificationPage(pageSize === 1 ? [] : [note(), note({ id: "n-2" })], 2)),
      );
    const api = fakeNotificationApi({ list });
    render(<NotificationBell api={api} pollMs={SLOW} />);
    const user = userEvent.setup();
    expect(await screen.findByRole("button", { name: "Notifications, 2 unread" })).toBeInTheDocument();
    await user.click(bell());
    await user.click(await screen.findByRole("button", { name: "Mark all as read" }));
    expect(api.markAllRead).toHaveBeenCalledOnce();
    expect(await screen.findByRole("button", { name: "Notifications" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Mark all as read" })).toBeDisabled();
  });

  it("shows an error when marking all fails and keeps the badge", async () => {
    const list = vi.fn().mockResolvedValue(notificationPage([note()], 1));
    const api = fakeNotificationApi({
      list,
      markAllRead: vi.fn().mockRejectedValue(problem(500, "Try again later.")),
    });
    render(<NotificationBell api={api} pollMs={SLOW} />);
    const user = userEvent.setup();
    await user.click(await screen.findByRole("button", { name: "Notifications, 1 unread" }));
    await user.click(await screen.findByRole("button", { name: "Mark all as read" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Try again later.");
    expect(bell()).toHaveAccessibleName("Notifications, 1 unread");
  });

  it("loads more notifications with the page token", async () => {
    const list = vi
      .fn()
      .mockImplementation(({ pageSize, pageToken }: { pageSize?: number; pageToken?: string }) => {
        if (pageSize === 1) return Promise.resolve(notificationPage([], 2));
        if (pageToken === "t1")
          return Promise.resolve(notificationPage([note({ id: "n-2", message: "Second page." })], 2));
        return Promise.resolve(notificationPage([note({ message: "First page." })], 2, "t1"));
      });
    render(<NotificationBell api={fakeNotificationApi({ list })} pollMs={SLOW} />);
    const user = userEvent.setup();
    await user.click(bell());
    await screen.findByText("First page.");
    await user.click(screen.getByRole("button", { name: "Load more" }));
    expect(await screen.findByText("Second page.")).toBeInTheDocument();
    expect(screen.getByText("First page.")).toBeInTheDocument();
    expect(list).toHaveBeenCalledWith({ pageSize: 20, pageToken: "t1" });
    expect(screen.queryByRole("button", { name: "Load more" })).not.toBeInTheDocument();
  });

  it("shows errors of the list and of loading more", async () => {
    const list = vi
      .fn()
      .mockImplementation(({ pageSize, pageToken }: { pageSize?: number; pageToken?: string }) => {
        if (pageSize === 1) return Promise.resolve(notificationPage([], 1));
        if (pageToken) return Promise.reject(problem(400, "The page token is not valid."));
        return Promise.resolve(notificationPage([note()], 1, "t1"));
      });
    const { unmount } = render(<NotificationBell api={fakeNotificationApi({ list })} pollMs={SLOW} />);
    const user = userEvent.setup();
    await user.click(bell());
    await user.click(await screen.findByRole("button", { name: "Load more" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("The page token is not valid.");
    unmount();

    const failing = vi
      .fn()
      .mockImplementation(({ pageSize }: { pageSize?: number }) =>
        pageSize === 1 ? Promise.resolve(notificationPage([], 0)) : Promise.reject(new Error("down")),
      );
    render(<NotificationBell api={fakeNotificationApi({ list: failing })} pollMs={SLOW} />);
    await userEvent.setup().click(bell());
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong");
    expect(screen.queryByText("No notifications.")).not.toBeInTheDocument();
  });

  it("closes with Escape (focus returns to the bell) and with a click outside", async () => {
    render(
      <div>
        <NotificationBell api={fakeNotificationApi()} pollMs={SLOW} />
        <p>Elsewhere</p>
      </div>,
    );
    const user = userEvent.setup();
    await user.click(bell());
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    await user.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(bell()).toHaveFocus();
    await user.click(bell());
    await user.keyboard("a"); // another key does nothing
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(within(screen.getByRole("dialog")).getByText("Notifications")); // inside: stays open
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    await user.click(screen.getByText("Elsewhere"));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("refreshes the open panel when a poll finds a new notification", async () => {
    let unread = 1;
    const list = vi
      .fn()
      .mockImplementation(({ pageSize }: { pageSize?: number }) =>
        Promise.resolve(
          pageSize === 1
            ? notificationPage([], unread)
            : notificationPage(
                unread === 1
                  ? [note({ message: "Only one." })]
                  : [note({ id: "n-2", message: "A new one." }), note({ message: "Only one." })],
                unread,
              ),
        ),
      );
    render(<NotificationBell api={fakeNotificationApi({ list })} pollMs={40} />);
    await userEvent.setup().click(bell());
    await screen.findByText("Only one.");
    unread = 2;
    expect(await screen.findByText("A new one.")).toBeInTheDocument();
  });
});
