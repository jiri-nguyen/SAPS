import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { UNAUTHORIZED, unauthorizedEvents } from "./api/client";
import type { SessionApi, UserAccount } from "./api/session";
import { browser } from "./auth/browser";
import { useSession } from "./auth/session-context";
import { fakeExceptionApi, summary } from "./test/invoices";
import { fakeNotificationApi, notificationFixture, notificationPage } from "./test/notifications";
import { fakeSettingsApi } from "./test/settings";

const MEMBER: UserAccount = {
  id: "1",
  username: "member1@vn.example.com",
  displayName: "Accounting Member 1",
  role: "ACCOUNTING_MEMBER",
  companyName: "Demo Vietnam",
};
const MANAGER: UserAccount = {
  id: "2",
  username: "manager1@vn.example.com",
  displayName: "Accounting Manager 1",
  role: "ACCOUNTING_MANAGER",
  companyName: "Demo Vietnam",
};
const pending = () => new Promise<never>(() => {});
const LOGOUT_URL = "http://localhost:8080/realms/saps/protocol/openid-connect/logout?client_id=saps-web";

function fakeApi(overrides: Partial<SessionApi> = {}): SessionApi {
  return {
    getSession: vi.fn().mockResolvedValue(null),
    signOut: vi.fn().mockResolvedValue(LOGOUT_URL),
    ...overrides,
  };
}

function renderApp(api: SessionApi, checkHealth: () => Promise<"ok" | "unreachable"> = pending) {
  return render(<App sessionApi={api} checkHealth={checkHealth} />);
}

function spyOnNavigation() {
  return vi.spyOn(browser, "assign").mockImplementation(() => {});
}

describe("App", () => {
  it("shows a loading state while the session is read", () => {
    renderApp(fakeApi({ getSession: pending }));
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("shows the sign-in page and the API health when not signed in", async () => {
    renderApp(fakeApi(), () => Promise.resolve("ok"));
    expect(await screen.findByRole("form", { name: "Sign in" })).toBeInTheDocument();
    expect(await screen.findByText("ok")).toBeInTheDocument();
  });

  it("falls back to the sign-in page when the session cannot be read", async () => {
    renderApp(fakeApi({ getSession: vi.fn().mockRejectedValue(new Error("down")) }));
    expect(await screen.findByRole("form", { name: "Sign in" })).toBeInTheDocument();
  });

  it("shows only the member menu to a signed-in member", async () => {
    renderApp(fakeApi({ getSession: vi.fn().mockResolvedValue(MEMBER) }));
    expect(await screen.findByTestId("signed-in-user")).toHaveTextContent(
      "Accounting Member 1 (Accounting Member) · Demo Vietnam", // the company (SAPS-42 TS-06)
    );
    const menu = screen.getByRole("navigation", { name: "Main menu" });
    expect(menu).toHaveTextContent("Upload invoices");
    expect(menu).toHaveTextContent("Review queue");
    expect(menu).not.toHaveTextContent("Approval queue");
    expect(menu).not.toHaveTextContent("Matching settings");
  });

  it("opens the upload page from the member menu", async () => {
    const invoiceApi = { upload: vi.fn(), get: vi.fn() };
    render(
      <App
        sessionApi={fakeApi({ getSession: vi.fn().mockResolvedValue(MEMBER) })}
        checkHealth={pending}
        invoiceApi={invoiceApi}
      />,
    );
    expect(await screen.findByRole("heading", { name: "Upload invoices" })).toBeInTheDocument();
    expect(screen.getByLabelText("Choose files")).toBeInTheDocument();
  });

  it("routes to the exception queue and to an invoice (SAPS-20)", async () => {
    const exceptionApi = fakeExceptionApi();
    window.location.hash = "#/exceptions";
    const { unmount } = render(
      <App
        sessionApi={fakeApi({ getSession: vi.fn().mockResolvedValue(MEMBER) })}
        checkHealth={pending}
        exceptionApi={exceptionApi}
      />,
    );
    expect(await screen.findByRole("heading", { name: "Exception queue" })).toBeInTheDocument();
    expect(await screen.findByText("No invoices in this queue.")).toBeInTheDocument();
    unmount();
    window.location.hash = "#/invoices/inv-12";
    render(
      <App
        sessionApi={fakeApi({ getSession: vi.fn().mockResolvedValue(MEMBER) })}
        checkHealth={pending}
        exceptionApi={exceptionApi}
      />,
    );
    expect(await screen.findByRole("heading", { name: "Invoice" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "← Exception queue" })).toHaveAttribute(
      "href",
      "#/exceptions",
    );
    expect(screen.getByRole("link", { name: "Exception queue" })).toHaveAttribute("aria-current", "page");
    expect(exceptionApi.getVersioned).toHaveBeenCalledWith("inv-12");
  });

  it("shows the approval queue and an invoice to approve to a manager (SAPS-22)", async () => {
    const exceptionApi = fakeExceptionApi({
      list: vi.fn().mockResolvedValue({
        items: [{ ...summary(), status: "PENDING_APPROVAL", openExceptionCodes: [] }],
        nextPageToken: null,
      }),
    });
    render(
      <App
        sessionApi={fakeApi({ getSession: vi.fn().mockResolvedValue(MANAGER) })}
        checkHealth={pending}
        exceptionApi={exceptionApi}
      />,
    );
    expect(await screen.findByRole("heading", { name: "Approval queue" })).toBeInTheDocument();
    expect(await screen.findByRole("link", { name: "AOS-2026-1013" })).toHaveAttribute(
      "href",
      "#/approvals/inv-12",
    );
    expect(exceptionApi.list).toHaveBeenCalledWith({ status: ["PENDING_APPROVAL"] });
    await userEvent.setup().click(screen.getByRole("link", { name: "AOS-2026-1013" }));
    expect(await screen.findByRole("link", { name: "← Approval queue" })).toBeInTheDocument();
    expect(exceptionApi.getVersioned).toHaveBeenCalledWith("inv-12");
  });

  it("shows the review queue and an invoice to review to a member (SAPS-21)", async () => {
    const exceptionApi = fakeExceptionApi({
      list: vi.fn().mockResolvedValue({
        items: [{ ...summary(), status: "PENDING_REVIEW", openExceptionCodes: [] }],
        nextPageToken: null,
      }),
    });
    window.location.hash = "#/review";
    render(
      <App
        sessionApi={fakeApi({ getSession: vi.fn().mockResolvedValue(MEMBER) })}
        checkHealth={pending}
        exceptionApi={exceptionApi}
      />,
    );
    expect(await screen.findByRole("heading", { name: "Review queue" })).toBeInTheDocument();
    expect(exceptionApi.list).toHaveBeenCalledWith({ status: ["PENDING_REVIEW"] });
    await userEvent.setup().click(await screen.findByRole("link", { name: "AOS-2026-1013" }));
    expect(await screen.findByRole("link", { name: "← Review queue" })).toBeInTheDocument();
    expect(window.location.hash).toBe("#/review/inv-12");
  });

  it("does not open the review queue for a manager", async () => {
    window.location.hash = "#/review/inv-12";
    render(
      <App sessionApi={fakeApi({ getSession: vi.fn().mockResolvedValue(MANAGER) })} checkHealth={pending} />,
    );
    expect(await screen.findByRole("heading", { name: "Approval queue" })).toBeInTheDocument();
  });

  it("does not open the approval queue for a member", async () => {
    window.location.hash = "#/approvals/inv-12";
    render(
      <App sessionApi={fakeApi({ getSession: vi.fn().mockResolvedValue(MEMBER) })} checkHealth={pending} />,
    );
    expect(await screen.findByRole("heading", { name: "Upload invoices" })).toBeInTheDocument();
  });

  it("opens the first screen for a route the role may not use", async () => {
    window.location.hash = "#/upload";
    render(
      <App sessionApi={fakeApi({ getSession: vi.fn().mockResolvedValue(MANAGER) })} checkHealth={pending} />,
    );
    expect(await screen.findByRole("heading", { name: "Approval queue" })).toBeInTheDocument();
  });

  it("shows only the manager menu for a manager and switches screens", async () => {
    const settingsApi = fakeSettingsApi();
    render(
      <App
        sessionApi={fakeApi({ getSession: vi.fn().mockResolvedValue(MANAGER) })}
        checkHealth={pending}
        settingsApi={settingsApi}
      />,
    );
    const menu = await screen.findByRole("navigation", { name: "Main menu" });
    expect(menu).not.toHaveTextContent("Upload invoices");
    expect(menu).toHaveTextContent("Exception queue"); // read-only for managers (SAPS-20, DEC-036)
    expect(screen.getByRole("heading", { name: "Approval queue" })).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("link", { name: "Matching settings" }));
    expect(await screen.findByRole("heading", { name: "Matching settings" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Matching settings" })).toHaveAttribute("aria-current", "page");
    expect(window.location.hash).toBe("#/matching-settings");
    expect(await screen.findByRole("form", { name: "Change matching settings" })).toBeInTheDocument();
    expect(settingsApi.get).toHaveBeenCalledOnce();
  });

  it.each([
    ["a member", MEMBER],
    ["a manager", MANAGER],
  ])(
    "shows %s the notification bell and opens the invoice of a notification (SAPS-24)",
    async (_label, user) => {
      const list = vi
        .fn()
        .mockImplementation(({ pageSize }: { pageSize?: number }) =>
          Promise.resolve(
            notificationPage(
              pageSize === 1
                ? []
                : [notificationFixture({ type: "APPROVAL_REQUESTED", message: "Invoice X needs approval." })],
              1,
            ),
          ),
        );
      const notificationApi = fakeNotificationApi({ list });
      render(
        <App
          sessionApi={fakeApi({ getSession: vi.fn().mockResolvedValue(user) })}
          checkHealth={pending}
          notificationApi={notificationApi}
          exceptionApi={fakeExceptionApi()}
        />,
      );
      const person = userEvent.setup();
      await person.click(await screen.findByRole("button", { name: "Notifications, 1 unread" }));
      await person.click(await screen.findByText("Invoice X needs approval."));
      expect(window.location.hash).toBe("#/approvals/inv-12");
      expect(notificationApi.markRead).toHaveBeenCalledWith("n-1");
    },
  );

  it("starts the sign-in through the company account and comes back to the same screen", async () => {
    const navigate = spyOnNavigation();
    window.location.hash = "#/exceptions";
    renderApp(fakeApi());
    await userEvent
      .setup()
      .click(await screen.findByRole("button", { name: "Sign in with your company account" }));
    expect(navigate).toHaveBeenCalledWith("/v1/session/sign-in?returnTo=%2F%23%2Fexceptions");
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    navigate.mockRestore();
    window.location.hash = "";
  });

  it.each([
    ["no_company", "Your account is not assigned to exactly one company. Ask your administrator."],
    ["wrong_domain", "Your e-mail address does not belong to your company. Ask your administrator."],
    ["no_role", "Your account needs exactly one SAPS role. Ask your administrator."],
    ["cancelled", "Sign-in was cancelled. Try again."],
    ["expired", "Your sign-in took too long or was started in another tab. Try again."],
    ["unavailable", "Sign-in is not available at the moment. Try again later."],
    ["something-new", "Sign-in is not available at the moment. Try again later."],
  ])("shows the reason %s of a refused sign-in once", async (reason, message) => {
    window.history.replaceState(null, "", `/?keep=1&signIn=${reason}#/`);
    renderApp(fakeApi());
    expect(await screen.findByRole("alert")).toHaveTextContent(message);
    expect(window.location.search).toBe("?keep=1"); // a reload does not show it again
    expect(window.location.hash).toBe("#/");
    window.history.replaceState(null, "", "/");
  });

  it("signs out and sends the browser to Keycloak to end that session too", async () => {
    const navigate = spyOnNavigation();
    const api = fakeApi({ getSession: vi.fn().mockResolvedValue(MEMBER) });
    renderApp(api);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Sign out" }));
    expect(api.signOut).toHaveBeenCalledOnce();
    expect(navigate).toHaveBeenCalledWith(LOGOUT_URL);
    navigate.mockRestore();
  });

  it("signs out locally when the call fails", async () => {
    const navigate = spyOnNavigation();
    const signOut = vi.fn().mockRejectedValue(new Error("offline"));
    renderApp(fakeApi({ getSession: vi.fn().mockResolvedValue(MEMBER), signOut }));
    await userEvent.setup().click(await screen.findByRole("button", { name: "Sign out" }));
    expect(signOut).toHaveBeenCalledOnce();
    expect(await screen.findByRole("form", { name: "Sign in" })).toBeInTheDocument();
    expect(navigate).not.toHaveBeenCalled();
    navigate.mockRestore();
  });

  it("returns to the sign-in page on any 401", async () => {
    renderApp(fakeApi({ getSession: vi.fn().mockResolvedValue(MEMBER) }));
    await screen.findByTestId("signed-in-user");
    act(() => {
      unauthorizedEvents.dispatchEvent(new Event(UNAUTHORIZED));
    });
    expect(await screen.findByRole("form", { name: "Sign in" })).toBeInTheDocument();
  });

  it("ignores results that arrive after unmount", async () => {
    let resolveSession: (user: UserAccount) => void = () => {};
    let resolveHealth: (value: "ok") => void = () => {};
    const { unmount } = renderApp(
      fakeApi({ getSession: () => new Promise((r) => (resolveSession = r)) }),
      () => new Promise((r) => (resolveHealth = r)),
    );
    unmount();
    resolveSession(MEMBER);
    resolveHealth("ok");
    await new Promise((resolve) => setTimeout(resolve, 0));
  });

  it("uses the real session API by default", () => {
    vi.stubGlobal("fetch", vi.fn(pending));
    render(<App checkHealth={pending} />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    vi.unstubAllGlobals();
  });
});

describe("useSession", () => {
  it("fails outside the provider", () => {
    vi.spyOn(console, "error").mockImplementation(() => {});
    expect(() => renderHook(() => useSession())).toThrow("useSession must be used inside SessionProvider");
    vi.restoreAllMocks();
  });
});
