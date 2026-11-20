import { describe, expect, it } from "vitest";

import { decimal, refusedCodes, text, timestamp } from "./format";

describe("format", () => {
  it("names the codes that cannot be accepted as is, once and in order", () => {
    expect(refusedCodes(["EX10", "EX2", "EX3", "EX3", "EX9", "EX6", "EX7"])).toEqual(["EX3", "EX10"]);
    expect(refusedCodes(["EX2", "EX6"])).toEqual([]);
  });

  it.each([
    ["20.6000", 2, "20.60"],
    ["300.00", 2, "300.00"],
    ["4.000", 0, "4"],
    ["4.500", 0, "4.5"],
    ["12", 2, "12.00"],
    [null, 2, "—"],
    [undefined, 2, "—"],
  ])("shows %s with %i decimals as %s", (value, places, shown) => {
    expect(decimal(value, places)).toBe(shown);
  });

  it("shows timestamps in UTC and empty values as a dash", () => {
    expect(timestamp("2026-12-15T09:30:12.345Z")).toBe("2026-12-15 09:30 UTC");
    expect(text(null)).toBe("—");
    expect(text("")).toBe("—");
    expect(text(3)).toBe("3");
  });
});
