import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "../api/client";
import { fakeSettingsApi, settingsFixture } from "../test/settings";
import { MatchingSettingsPage } from "./MatchingSettingsPage";

const problem = (status: number, errors: { field?: string; message?: string }[], detail = "Not valid.") =>
  new ApiError(status, { type: "about:blank", title: "x", status, detail, errors });

const tolerance = () => screen.getByRole("textbox", { name: /Price tolerance/ });
const threshold = () => screen.getByRole("textbox", { name: /Approval threshold/ });
const save = () => screen.getByRole("button", { name: "Save settings" });

async function replace(field: HTMLElement, value: string) {
  const user = userEvent.setup();
  await user.clear(field);
  if (value !== "") await user.type(field, value);
  return user;
}

describe("matching settings screen (SAPS-28)", () => {
  it("shows the current values and who changed them last (BR-05)", async () => {
    render(<MatchingSettingsPage api={fakeSettingsApi()} />);
    expect(await screen.findByText("Last changed by system on 2026-12-01 08:00 UTC.")).toBeInTheDocument();
    expect(tolerance()).toHaveValue("0.50");
    expect(threshold()).toHaveValue("300.00");
    expect(screen.getByText(/0 means the prices must be equal/)).toBeInTheDocument();
    expect(screen.getByText(/already processed keep the values/)).toBeInTheDocument();
  });

  it("saves both values and shows the new last change", async () => {
    const update = vi.fn().mockResolvedValue(
      settingsFixture({
        priceToleranceUsd: "1.0000",
        approvalThresholdUsd: "450.50",
        updatedBy: "Accounting Manager 1",
        updatedAt: "2026-12-15T10:15:00Z",
      }),
    );
    render(<MatchingSettingsPage api={fakeSettingsApi({ update })} />);
    await screen.findByText(/Last changed by system/);
    const user = await replace(tolerance(), " 1.00 ");
    await user.clear(threshold());
    await user.type(threshold(), "450.5");
    await user.click(save());
    expect(update).toHaveBeenCalledWith({ priceToleranceUsd: "1.00", approvalThresholdUsd: "450.5" });
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Saved. The new values apply to the next matching runs.",
    );
    expect(
      screen.getByText("Last changed by Accounting Manager 1 on 2026-12-15 10:15 UTC."),
    ).toBeInTheDocument();
    expect(tolerance()).toHaveValue("1.00");
    expect(threshold()).toHaveValue("450.50");
  });

  it("accepts 0 for both values (DEC-045)", async () => {
    const update = vi
      .fn()
      .mockResolvedValue(settingsFixture({ priceToleranceUsd: "0", approvalThresholdUsd: "0" }));
    render(<MatchingSettingsPage api={fakeSettingsApi({ update })} />);
    await screen.findByText(/Last changed by/);
    const user = await replace(tolerance(), "0");
    await user.clear(threshold());
    await user.type(threshold(), "0");
    await user.click(save());
    expect(update).toHaveBeenCalledWith({ priceToleranceUsd: "0", approvalThresholdUsd: "0" });
  });

  it.each([
    ["", "Enter the price tolerance"],
    ["abc", "Enter the price tolerance"],
    ["-1", "Enter the price tolerance"],
    ["0.12345", "up to 4 decimals"],
  ])("refuses the price tolerance %j before sending", async (value, message) => {
    const update = vi.fn();
    render(<MatchingSettingsPage api={fakeSettingsApi({ update })} />);
    await screen.findByText(/Last changed by/);
    const user = await replace(tolerance(), value);
    await user.click(save());
    expect(screen.getByRole("alert")).toHaveTextContent(message);
    expect(tolerance()).toHaveAttribute("aria-invalid", "true");
    expect(update).not.toHaveBeenCalled();
  });

  it("refuses an approval threshold with more than 2 decimals and clears the message after a fix", async () => {
    const update = vi.fn().mockResolvedValue(settingsFixture({ approvalThresholdUsd: "300.12" }));
    render(<MatchingSettingsPage api={fakeSettingsApi({ update })} />);
    await screen.findByText(/Last changed by/);
    const user = await replace(threshold(), "300.123");
    await user.click(save());
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Enter the approval threshold as a number of 0 or more with up to 2 decimals.",
    );
    expect(update).not.toHaveBeenCalled();
    await user.clear(threshold());
    await user.type(threshold(), "300.12");
    await user.click(save());
    expect(await screen.findByRole("status")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("shows the field named by the server (422)", async () => {
    const update = vi
      .fn()
      .mockRejectedValue(
        problem(422, [{ field: "priceToleranceUsd", message: "The price tolerance must be 0 or more." }]),
      );
    render(<MatchingSettingsPage api={fakeSettingsApi({ update })} />);
    await screen.findByText(/Last changed by/);
    await userEvent.setup().click(save());
    expect(await screen.findByRole("alert")).toHaveTextContent("The price tolerance must be 0 or more.");
    expect(tolerance()).toHaveAttribute("aria-invalid", "true");
    expect(threshold()).toHaveAttribute("aria-invalid", "false");
    expect(screen.queryByRole("status")).not.toBeInTheDocument();
  });

  it("shows other save errors as a message, with a fallback for unnamed fields", async () => {
    const update = vi
      .fn()
      .mockRejectedValueOnce(problem(422, [{ field: "approvalThresholdUsd" }]))
      .mockRejectedValueOnce(problem(403, [], "Your role is not allowed for this operation."))
      .mockRejectedValue(new Error("network down"));
    render(<MatchingSettingsPage api={fakeSettingsApi({ update })} />);
    await screen.findByText(/Last changed by/);
    const user = userEvent.setup();
    await user.click(save());
    expect(await screen.findByRole("alert")).toHaveTextContent("The value is not valid.");
    await user.click(save());
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Your role is not allowed for this operation.",
    );
    await user.click(save());
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong");
  });

  it("shows an error when the settings cannot be read, and waits while loading", async () => {
    const get = vi.fn().mockRejectedValue(problem(403, [], "Your role is not allowed for this operation."));
    const { unmount } = render(<MatchingSettingsPage api={fakeSettingsApi({ get })} />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
    expect(await screen.findByRole("alert")).toHaveTextContent("Your role is not allowed");
    unmount();
    const pending = new Promise<never>(() => {});
    render(<MatchingSettingsPage api={fakeSettingsApi({ get: () => pending })} />);
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });
});
