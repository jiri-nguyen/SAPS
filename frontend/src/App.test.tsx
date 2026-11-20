import { act, render, renderHook, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { App } from "./App";
import { ApiError, UNAUTHORIZED, unauthorizedEvents } from "./api/client";
import type { SessionApi, UserAccount } from "./api/session";
import { useSession } from "./auth/session-context";
import { fakeExceptionApi, summary } from "./test/invoices";

const MEMBER: UserAccount = {
  id: "1",
  username: "member1",
  displayName: "Accounting Member 1",
  role: "ACCOUNTING_MEMBER",
};
const MANAGER: UserAccount = {
  id: "2",
  username: "manager1",
  displayName: "Accounting Manager 1",
  role: "ACCOUNTING_MANAGER",
};
const pending = () => new Promise<never>(() => {});

function fakeApi(overrides: Partial<SessionApi> = {}): SessionApi {
  return {
    getSession: vi.fn().mockResolvedValue(null),
    signIn: vi.fn().mockResolvedValue(MEMBER),
    signOut: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

function renderApp(api: SessionApi, checkHealth: () => Promise<"ok" | "unreachable"> = pending) {
  return render(<App sessionApi={api} checkHealth={checkHealth} />);
}

async function signInAs(username: string, password = "pw") {
  const user = userEvent.setup();
  await user.type(await screen.findByLabelText("Username"), username);
  await user.type(screen.getByLabelText("Password"), password);
  await user.click(screen.getByRole("button", { name: "Sign in" }));
  return user;
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

  it("signs in a member and shows only the member menu", async () => {
    const api = fakeApi();
    renderApp(api);
    await signInAs(" member1 ");
    expect(api.signIn).toHaveBeenCalledWith("member1", "pw");
    expect(await screen.findByTestId("signed-in-user")).toHaveTextContent(
      "Accounting Member 1 (Accounting Member)",
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
    renderApp(fakeApi({ getSession: vi.fn().mockResolvedValue(MANAGER) }));
    const menu = await screen.findByRole("navigation", { name: "Main menu" });
    expect(menu).not.toHaveTextContent("Upload invoices");
    expect(menu).toHaveTextContent("Exception queue"); // read-only for managers (SAPS-20, DEC-036)
    expect(screen.getByRole("heading", { name: "Approval queue" })).toBeInTheDocument();
    await userEvent.setup().click(screen.getByRole("link", { name: "Matching settings" }));
    expect(await screen.findByRole("heading", { name: "Matching settings" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Matching settings" })).toHaveAttribute("aria-current", "page");
    expect(window.location.hash).toBe("#/matching-settings");
  });

  it("shows one message for a wrong username or password", async () => {
    const signIn = vi.fn().mockRejectedValue(new ApiError(401));
    renderApp(fakeApi({ signIn }));
    await signInAs("member1", "wrong");
    expect(await screen.findByRole("alert")).toHaveTextContent("Invalid username or password.");
    expect(screen.getByLabelText("Password")).toHaveValue("");
    expect(screen.getByRole("button", { name: "Sign in" })).toBeEnabled();
  });

  it("shows a general message for other sign-in errors", async () => {
    renderApp(fakeApi({ signIn: vi.fn().mockRejectedValue(new ApiError(503)) }));
    await signInAs("member1");
    expect(await screen.findByRole("alert")).toHaveTextContent("Sign-in failed. Please try again.");
  });

  it("signs out and returns to the sign-in page, even when the call fails", async () => {
    const signOut = vi.fn().mockRejectedValue(new Error("offline"));
    renderApp(fakeApi({ getSession: vi.fn().mockResolvedValue(MEMBER), signOut }));
    await userEvent.setup().click(await screen.findByRole("button", { name: "Sign out" }));
    expect(signOut).toHaveBeenCalledOnce();
    expect(await screen.findByRole("form", { name: "Sign in" })).toBeInTheDocument();
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
