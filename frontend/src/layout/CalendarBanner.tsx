import { useEffect, useState } from "react";

import type { CalendarApi, ProcessingCalendar } from "../api/calendar";

/**
 * On a closed day of the processing calendar every user sees that new invoices are held (SAPS-52 BR-08, DEC-062).
 * A calendar that cannot be read shows no banner: it is information, not a gate.
 */
export function CalendarBanner({
  api,
  company,
  refreshKey,
}: {
  api: CalendarApi;
  company: string | undefined;
  refreshKey: string;
}) {
  const [calendar, setCalendar] = useState<ProcessingCalendar | null>(null);

  useEffect(() => {
    let active = true;
    api.get().then(
      (loaded) => active && setCalendar(loaded),
      () => active && setCalendar(null),
    );
    return () => {
      active = false;
    };
  }, [api, refreshKey]);

  if (calendar === null || !calendar.closedToday) return null;
  const until = calendar.openAgainOn ? `until ${calendar.openAgainOn}` : "until further notice";
  return (
    <p className="banner info" role="status" data-testid="calendar-banner">
      {company ?? "The company"} is in a closed period {until}: new invoices are held.
    </p>
  );
}
