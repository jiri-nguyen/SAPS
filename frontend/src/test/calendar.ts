import { vi } from "vitest";

import type { CalendarApi, ProcessingCalendar } from "../api/calendar";

/** An open company in Singapore (SAPS-52). */
export function calendarFixture(overrides: Partial<ProcessingCalendar> = {}): ProcessingCalendar {
  return {
    rules: [],
    timeZone: "Asia/Singapore",
    closedToday: false,
    openAgainOn: null,
    updatedAt: null,
    updatedBy: null,
    ...overrides,
  };
}

export function fakeCalendarApi(overrides: Partial<CalendarApi> = {}): CalendarApi {
  return {
    get: vi.fn().mockResolvedValue(calendarFixture()),
    replace: vi.fn().mockResolvedValue(calendarFixture()),
    ...overrides,
  };
}
