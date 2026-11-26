import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { calendarFixture, fakeCalendarApi } from "../test/calendar";
import { CalendarBanner } from "./CalendarBanner";

describe("calendar banner (SAPS-52 BR-08)", () => {
  it("says until when the company is closed", async () => {
    const api = fakeCalendarApi({
      get: vi.fn().mockResolvedValue(calendarFixture({ closedToday: true, openAgainOn: "2027-04-06" })),
    });
    render(<CalendarBanner api={api} company="Demo Singapore" refreshKey="x" />);
    expect(await screen.findByTestId("calendar-banner")).toHaveTextContent(
      "Demo Singapore is in a closed period until 2027-04-06: new invoices are held.",
    );
  });

  it("says until further notice when no open day follows", async () => {
    const api = fakeCalendarApi({
      get: vi.fn().mockResolvedValue(calendarFixture({ closedToday: true, openAgainOn: null })),
    });
    render(<CalendarBanner api={api} company={undefined} refreshKey="x" />);
    expect(await screen.findByTestId("calendar-banner")).toHaveTextContent(
      "The company is in a closed period until further notice: new invoices are held.",
    );
  });

  it("shows nothing for an open company or a calendar that cannot be read", async () => {
    const { unmount } = render(<CalendarBanner api={fakeCalendarApi()} company="A" refreshKey="x" />);
    await vi.waitFor(() => expect(screen.queryByTestId("calendar-banner")).not.toBeInTheDocument());
    unmount();
    const api = fakeCalendarApi({ get: vi.fn().mockRejectedValue(new Error("down")) });
    render(<CalendarBanner api={api} company="A" refreshKey="x" />);
    await vi.waitFor(() => expect(api.get).toHaveBeenCalled());
    expect(screen.queryByTestId("calendar-banner")).not.toBeInTheDocument();
  });

  it("reads the calendar again when the key changes and ignores a late answer", async () => {
    const get = vi.fn().mockResolvedValue(calendarFixture());
    const { rerender, unmount } = render(
      <CalendarBanner api={fakeCalendarApi({ get })} company="A" refreshKey="a" />,
    );
    rerender(<CalendarBanner api={fakeCalendarApi({ get })} company="A" refreshKey="b" />);
    await vi.waitFor(() => expect(get).toHaveBeenCalledTimes(2));
    let resolve: (value: ReturnType<typeof calendarFixture>) => void = () => {};
    const late = vi.fn().mockReturnValue(new Promise((r) => (resolve = r)));
    unmount();
    const second = render(<CalendarBanner api={fakeCalendarApi({ get: late })} company="A" refreshKey="c" />);
    second.unmount();
    resolve(calendarFixture({ closedToday: true }));
    await Promise.resolve();
    expect(screen.queryByTestId("calendar-banner")).not.toBeInTheDocument();
  });
});
