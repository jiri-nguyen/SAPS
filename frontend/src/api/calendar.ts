import { apiFetch } from "./client";
import type { components } from "./schema";

export type ProcessingCalendar = components["schemas"]["ProcessingCalendar"];
export type CalendarRule = components["schemas"]["CalendarRule"];

/** Processing calendar operations of the SAPS API (SAPS-52): both roles read it, Accounting Managers replace it. */
export interface CalendarApi {
  get(): Promise<ProcessingCalendar>;
  replace(rules: CalendarRule[]): Promise<ProcessingCalendar>;
}

export function createCalendarApi(fetchImpl: typeof fetch = fetch): CalendarApi {
  return {
    async get() {
      const response = await apiFetch("/v1/processing-calendar", {}, fetchImpl);
      return (await response.json()) as ProcessingCalendar;
    },
    async replace(rules) {
      const response = await apiFetch(
        "/v1/processing-calendar",
        { method: "PUT", body: JSON.stringify({ rules }) },
        fetchImpl,
      );
      return (await response.json()) as ProcessingCalendar;
    },
  };
}
