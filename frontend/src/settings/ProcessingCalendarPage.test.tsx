import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { calendarFixture, fakeCalendarApi } from "../test/calendar";
import { ProcessingCalendarPage } from "./ProcessingCalendarPage";

const RULES = [
  { kind: "MONTHLY_RANGE" as const, fromDay: 25, toDay: 5, label: "Month end" },
  { kind: "WEEKDAY" as const, weekday: 6 },
  { kind: "DATE" as const, date: "2027-04-30", label: "Public holiday" },
];

describe("processing calendar screen (SAPS-52, UC-10)", () => {
  it("shows an open company without rules", async () => {
    render(<ProcessingCalendarPage api={fakeCalendarApi()} />);
    expect(await screen.findByText("No closed days: the company processes every day.")).toBeInTheDocument();
    expect(screen.getByTestId("calendar-summary")).toHaveTextContent("The company is open today.");
    expect(screen.getByText("Asia/Singapore")).toBeInTheDocument();
  });

  it("shows the rules and the first open day of a closed company", async () => {
    const api = fakeCalendarApi({
      get: vi.fn().mockResolvedValue(
        calendarFixture({
          rules: RULES,
          closedToday: true,
          openAgainOn: "2027-04-06",
          updatedAt: "2027-03-01T08:00:00Z",
          updatedBy: "Accounting Manager 1",
        }),
      ),
    });
    render(<ProcessingCalendarPage api={api} />);
    expect(await screen.findByLabelText("Rule 1 from day")).toHaveValue(25);
    expect(screen.getByLabelText("Rule 1 to day")).toHaveValue(5);
    expect(screen.getByLabelText("Rule 1 label")).toHaveValue("Month end");
    expect(screen.getByLabelText("Rule 2 weekday")).toHaveValue("6");
    expect(screen.getByLabelText("Rule 3 date")).toHaveValue("2027-04-30");
    expect(screen.getByTestId("calendar-summary")).toHaveTextContent(
      "The company is closed today. It is open again on 2027-04-06.",
    );
    expect(
      screen.getByText("Last changed by Accounting Manager 1 on 2027-03-01 08:00 UTC."),
    ).toBeInTheDocument();
  });

  it("says when no open day follows", async () => {
    const api = fakeCalendarApi({
      get: vi.fn().mockResolvedValue(calendarFixture({ closedToday: true, openAgainOn: null })),
    });
    render(<ProcessingCalendarPage api={api} />);
    expect(await screen.findByTestId("calendar-summary")).toHaveTextContent(
      "closed today and no open day follows within a year",
    );
  });

  it("adds, changes and removes rules and saves them all at once", async () => {
    const replace = vi.fn().mockResolvedValue(calendarFixture({ rules: RULES }));
    const onChanged = vi.fn();
    render(<ProcessingCalendarPage api={fakeCalendarApi({ replace })} onChanged={onChanged} />);
    const person = userEvent.setup();
    await screen.findByText("No closed days: the company processes every day.");

    await person.click(screen.getByRole("button", { name: "Add rule" }));
    await person.selectOptions(screen.getByLabelText("Rule 1 type"), "MONTHLY_RANGE");
    await person.type(screen.getByLabelText("Rule 1 from day"), "25");
    await person.type(screen.getByLabelText("Rule 1 to day"), "5");
    await person.type(screen.getByLabelText("Rule 1 label"), "  Month end ");
    await person.click(screen.getByRole("button", { name: "Add rule" })); // a weekday rule, Saturday by default
    await person.selectOptions(screen.getByLabelText("Rule 2 weekday"), "7");
    await person.click(screen.getByRole("button", { name: "Add rule" }));
    await person.selectOptions(screen.getByLabelText("Rule 3 type"), "DATE");
    await person.type(screen.getByLabelText("Rule 3 date"), "2027-04-30");
    await person.click(screen.getByRole("button", { name: "Add rule" }));
    await person.click(screen.getByRole("button", { name: "Remove rule 4" }));
    await person.click(screen.getByRole("button", { name: "Save calendar" }));

    expect(replace).toHaveBeenCalledWith([
      { kind: "MONTHLY_RANGE", fromDay: 25, toDay: 5, label: "Month end" },
      { kind: "WEEKDAY", weekday: 7 },
      { kind: "DATE", date: "2027-04-30" },
    ]);
    expect(await screen.findByText(/Saved. The calendar applies now/)).toBeInTheDocument();
    expect(onChanged).toHaveBeenCalledOnce();
  });

  it("sends only what a rule needs and lets the API name what is missing", async () => {
    const replace = vi
      .fn()
      .mockRejectedValue(new ApiError(422, { type: "about:blank", title: "x", status: 422 }));
    render(<ProcessingCalendarPage api={fakeCalendarApi({ replace })} />);
    const person = userEvent.setup();
    await screen.findByText("No closed days: the company processes every day.");
    await person.click(screen.getByRole("button", { name: "Add rule" }));
    await person.selectOptions(screen.getByLabelText("Rule 1 type"), "MONTHLY_RANGE");
    await person.click(screen.getByRole("button", { name: "Save calendar" }));
    expect(replace).toHaveBeenCalledWith([{ kind: "MONTHLY_RANGE" }]);
    await person.selectOptions(screen.getByLabelText("Rule 1 type"), "DATE");
    await person.click(screen.getByRole("button", { name: "Save calendar" }));
    expect(replace).toHaveBeenLastCalledWith([{ kind: "DATE" }]);
  });

  it("marks the refused rules and keeps the form (EC-10)", async () => {
    const problem = {
      type: "about:blank",
      title: "x",
      status: 422,
      errors: [
        { field: "rules[1].fromDay", message: "The day of the month is 1 to 31." },
        { field: "rules[1]", message: "A monthly range has only a first and a last day." },
        { field: "rules[0].weekday" },
      ],
    };
    const api = fakeCalendarApi({
      get: vi.fn().mockResolvedValue(
        calendarFixture({
          rules: [
            { kind: "WEEKDAY", weekday: 6 },
            { kind: "MONTHLY_RANGE", fromDay: 40, toDay: 5 },
          ],
        }),
      ),
      replace: vi.fn().mockRejectedValue(new ApiError(422, problem)),
    });
    render(<ProcessingCalendarPage api={api} />);
    await userEvent.setup().click(await screen.findByRole("button", { name: "Save calendar" }));
    expect(await screen.findByText("Correct the marked rules.")).toBeInTheDocument();
    const second = screen.getByRole("group", { name: "Rule 2" });
    expect(within(second).getByText("The day of the month is 1 to 31.")).toBeInTheDocument();
    expect(within(second).getByText("A monthly range has only a first and a last day.")).toBeInTheDocument();
    expect(
      within(screen.getByRole("group", { name: "Rule 1" })).getByText("The rule is not valid."),
    ).toBeInTheDocument();
    expect(screen.getByLabelText("Rule 2 from day")).toHaveValue(40);
  });

  it("shows other errors, when loading too, and removing a rule clears the marks", async () => {
    render(
      <ProcessingCalendarPage api={fakeCalendarApi({ get: vi.fn().mockRejectedValue(new ApiError(500)) })} />,
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("HTTP 500");

    const api = fakeCalendarApi({
      get: vi.fn().mockResolvedValue(calendarFixture({ rules: [{ kind: "WEEKDAY", weekday: 6 }] })),
      replace: vi.fn().mockRejectedValue(new Error("offline")),
    });
    render(<ProcessingCalendarPage api={api} />);
    const person = userEvent.setup();
    await person.click(await screen.findByRole("button", { name: "Save calendar" }));
    expect(await screen.findByText(/Something went wrong/)).toBeInTheDocument();
    await person.click(screen.getByRole("button", { name: "Remove rule 1" }));
    expect(screen.getByText("No closed days: the company processes every day.")).toBeInTheDocument();
  });

  it("stops adding at 100 rules", async () => {
    const rules = Array.from({ length: 100 }, () => ({ kind: "WEEKDAY" as const, weekday: 1 }));
    render(
      <ProcessingCalendarPage
        api={fakeCalendarApi({ get: vi.fn().mockResolvedValue(calendarFixture({ rules })) })}
      />,
    );
    expect(await screen.findByRole("button", { name: "Add rule" })).toBeDisabled();
    expect(screen.getByText("At most 100 rules.")).toBeInTheDocument();
  });

  it("ignores an answer that arrives after the screen was left", async () => {
    let resolve: (value: ReturnType<typeof calendarFixture>) => void = () => {};
    const { unmount } = render(
      <ProcessingCalendarPage api={fakeCalendarApi({ get: () => new Promise((r) => (resolve = r)) })} />,
    );
    unmount();
    resolve(calendarFixture());
    await Promise.resolve();
    expect(screen.queryByText("The company is open today.")).not.toBeInTheDocument();
  });
});
