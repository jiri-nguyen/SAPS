import { type FormEvent, useEffect, useState } from "react";

import { ApiError } from "../api/client";
import type { CalendarApi, CalendarRule, ProcessingCalendar } from "../api/calendar";
import { errorMessage } from "../invoices/errors";
import { timestamp } from "../invoices/format";

type Kind = CalendarRule["kind"];

/** A rule as the form edits it: every input is text until it is saved. */
interface Row {
  kind: Kind;
  fromDay: string;
  toDay: string;
  weekday: string;
  date: string;
  label: string;
}

const KIND_LABEL: Record<Kind, string> = {
  MONTHLY_RANGE: "Monthly range",
  WEEKDAY: "Weekday",
  DATE: "Specific date",
};
const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];
const MAX_RULES = 100;

function toRow(rule: CalendarRule): Row {
  return {
    kind: rule.kind,
    fromDay: rule.fromDay?.toString() ?? "",
    toDay: rule.toDay?.toString() ?? "",
    weekday: rule.weekday?.toString() ?? "",
    date: rule.date ?? "",
    label: rule.label ?? "",
  };
}

/** Only the fields of the rule's kind are sent; an empty input is left out, so the API names what is missing. */
function toRule(row: Row): CalendarRule {
  const rule: CalendarRule = { kind: row.kind };
  if (row.kind === "MONTHLY_RANGE") {
    if (row.fromDay.trim()) rule.fromDay = Number(row.fromDay);
    if (row.toDay.trim()) rule.toDay = Number(row.toDay);
  } else if (row.kind === "WEEKDAY") {
    if (row.weekday) rule.weekday = Number(row.weekday);
  } else if (row.date) {
    rule.date = row.date;
  }
  if (row.label.trim()) rule.label = row.label.trim();
  return rule;
}

/** The messages of the API for the rule at `index` (`rules[2].fromDay`, `rules[2]`), by field. */
function rowErrors(errors: { field?: string; message?: string }[], index: number): string[] {
  const prefix = `rules[${index}]`;
  return errors
    .filter((e) => e.field === prefix || e.field?.startsWith(`${prefix}.`))
    .map((e) => e.message ?? "The rule is not valid.");
}

function summary(calendar: ProcessingCalendar): string {
  if (!calendar.closedToday) return "The company is open today.";
  return calendar.openAgainOn
    ? `The company is closed today. It is open again on ${calendar.openAgainOn}.`
    : "The company is closed today and no open day follows within a year.";
}

/**
 * The processing calendar of the company (SAPS-52, UC-10): days on which new invoices are held instead of processed.
 * Only Accounting Managers open it; a change applies at once, also to invoices already held (BR-07).
 */
export function ProcessingCalendarPage({ api, onChanged }: { api: CalendarApi; onChanged?: () => void }) {
  const [calendar, setCalendar] = useState<ProcessingCalendar | null>(null);
  const [rows, setRows] = useState<Row[]>([]);
  const [problems, setProblems] = useState<{ field?: string; message?: string }[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    api.get().then(
      (loaded) => {
        if (!active) return;
        setCalendar(loaded);
        setRows(loaded.rules.map(toRow));
      },
      (caught: unknown) => {
        if (active) setError(errorMessage(caught));
      },
    );
    return () => {
      active = false;
    };
  }, [api]);

  function edit(index: number, change: Partial<Row>) {
    setRows((current) => current.map((row, i) => (i === index ? { ...row, ...change } : row)));
    setSaved(false);
  }

  function add() {
    setRows((current) => [
      ...current,
      { kind: "WEEKDAY", fromDay: "", toDay: "", weekday: "6", date: "", label: "" },
    ]);
    setSaved(false);
  }

  function remove(index: number) {
    setRows((current) => current.filter((_, i) => i !== index));
    setProblems([]);
    setSaved(false);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setProblems([]);
    try {
      const result = await api.replace(rows.map(toRule));
      setCalendar(result);
      setRows(result.rules.map(toRow));
      setSaved(true);
      onChanged?.();
    } catch (caught) {
      if (caught instanceof ApiError && caught.status === 422) {
        setProblems(caught.problem?.errors ?? []);
        setError("Correct the marked rules.");
      } else {
        setError(errorMessage(caught));
      }
    } finally {
      setBusy(false);
    }
  }

  if (calendar === null)
    return error !== null ? (
      <p role="alert" className="banner error">
        {error}
      </p>
    ) : (
      <p>Loading…</p>
    );

  return (
    <section aria-label="Processing calendar" className="stack">
      <p className="hint">
        New invoices received on a closed day are held (status On hold) and processed when the company is open
        again. Days are days of the company&apos;s time zone: <strong>{calendar.timeZone}</strong>. Invoices
        already in exception handling, approval or final review are worked on as usual.
      </p>
      <p data-testid="calendar-summary">{summary(calendar)}</p>
      <form
        aria-label="Processing calendar rules"
        className="settings-form stack"
        noValidate // the API names what is wrong (EC-10); no browser tooltip in its place
        onSubmit={(e) => void save(e)}
      >
        {rows.length === 0 && <p className="empty">No closed days: the company processes every day.</p>}
        {rows.map((row, index) => (
          <fieldset key={index} className="calendar-rule" aria-label={`Rule ${index + 1}`}>
            <label>
              Rule type
              <select
                value={row.kind}
                onChange={(e) => edit(index, { kind: e.target.value as Kind })}
                aria-label={`Rule ${index + 1} type`}
              >
                {(Object.keys(KIND_LABEL) as Kind[]).map((kind) => (
                  <option key={kind} value={kind}>
                    {KIND_LABEL[kind]}
                  </option>
                ))}
              </select>
            </label>
            {row.kind === "MONTHLY_RANGE" && (
              <>
                <label>
                  From day
                  <input
                    type="number"
                    min={1}
                    max={31}
                    value={row.fromDay}
                    aria-label={`Rule ${index + 1} from day`}
                    onChange={(e) => edit(index, { fromDay: e.target.value })}
                  />
                </label>
                <label>
                  To day
                  <input
                    type="number"
                    min={1}
                    max={31}
                    value={row.toDay}
                    aria-label={`Rule ${index + 1} to day`}
                    onChange={(e) => edit(index, { toDay: e.target.value })}
                  />
                </label>
              </>
            )}
            {row.kind === "WEEKDAY" && (
              <label>
                Weekday
                <select
                  value={row.weekday}
                  aria-label={`Rule ${index + 1} weekday`}
                  onChange={(e) => edit(index, { weekday: e.target.value })}
                >
                  {WEEKDAYS.map((name, i) => (
                    <option key={name} value={String(i + 1)}>
                      {name}
                    </option>
                  ))}
                </select>
              </label>
            )}
            {row.kind === "DATE" && (
              <label>
                Date
                <input
                  type="date"
                  value={row.date}
                  aria-label={`Rule ${index + 1} date`}
                  onChange={(e) => edit(index, { date: e.target.value })}
                />
              </label>
            )}
            <label>
              Label (optional)
              <input
                type="text"
                maxLength={100}
                value={row.label}
                aria-label={`Rule ${index + 1} label`}
                onChange={(e) => edit(index, { label: e.target.value })}
              />
            </label>
            <button type="button" className="secondary" onClick={() => remove(index)}>
              Remove rule {index + 1}
            </button>
            {rowErrors(problems, index).map((message) => (
              <span key={message} role="alert" className="field-error">
                {message}
              </span>
            ))}
          </fieldset>
        ))}
        {rows.length >= MAX_RULES && <p className="hint">At most {MAX_RULES} rules.</p>}
        <p className="hint">
          A monthly range includes both days and may run into the next month (25 to 5). A day after the end of
          a month means its last day.
        </p>
        {error !== null && (
          <p role="alert" className="banner error">
            {error}
          </p>
        )}
        {saved && (
          <p role="status" className="banner success">
            Saved. The calendar applies now, also to invoices already held.
          </p>
        )}
        <div className="toolbar">
          <button
            type="button"
            className="secondary"
            disabled={busy || rows.length >= MAX_RULES}
            onClick={add}
          >
            Add rule
          </button>
          <button type="submit" disabled={busy}>
            Save calendar
          </button>
        </div>
        {calendar.updatedAt && (
          <p className="hint">
            Last changed by {calendar.updatedBy ?? "unknown"} on {timestamp(calendar.updatedAt)}.
          </p>
        )}
      </form>
    </section>
  );
}
