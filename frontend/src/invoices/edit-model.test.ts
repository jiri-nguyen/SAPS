import { describe, expect, it } from "vitest";

import { invoiceFixture } from "../test/invoices";
import type { Invoice } from "../api/invoices";
import { type LineValues, changes, emptyLine, headerOf, linesOf, validate } from "./edit-model";

const INVOICE = invoiceFixture();
const ORIGINAL = { header: headerOf(INVOICE), lines: linesOf(INVOICE) };
const [LINE] = ORIGINAL.lines as [LineValues];
const [INVOICE_LINE] = INVOICE.lines as [Invoice["lines"][number]];

describe("edit model", () => {
  it("shows the invoice values without trailing zeros", () => {
    expect(ORIGINAL.header.totalAmount).toBe("90.64");
    expect(ORIGINAL.lines[0]).toMatchObject({ quantity: "4", unitPrice: "20.60", poNumber: "0100012" });
    const empty = invoiceFixture({ vendorCode: null, totalAmount: null, lines: [] });
    expect(headerOf(empty).vendorCode).toBe("");
    expect(linesOf(empty)).toEqual([]);
    const sparse = linesOf(
      invoiceFixture({
        lines: [{ ...INVOICE_LINE, description: null, poNumber: null, poLineNumber: null, quantity: null }],
      }),
    );
    expect(sparse[0]).toMatchObject({
      description: "",
      poNumber: "",
      poLineNumber: "",
      doNumber: "",
      quantity: "",
    });
    const withDo = linesOf(
      invoiceFixture({
        lines: [{ ...INVOICE_LINE, doNumber: "DO-7000021B", matchedDoNumber: "DO-7000021B" }],
      }),
    );
    expect(withDo[0]?.doNumber).toBe("DO-7000021B");
  });

  it("adds a line after the highest line number", () => {
    expect(emptyLine(ORIGINAL.lines).lineNumber).toBe("2");
    expect(emptyLine([]).lineNumber).toBe("1");
  });

  it("sends nothing when nothing changed", () => {
    expect(changes(ORIGINAL, { ...ORIGINAL.header }, [...ORIGINAL.lines])).toEqual({});
  });

  it("sends only changed header fields, and all lines when one line changed", () => {
    const lines = [{ ...LINE, unitPrice: "20.00" }];
    const body = changes(ORIGINAL, { ...ORIGINAL.header, vendorName: " Alpha Ltd. " }, lines);
    expect(body).toEqual({
      vendorName: "Alpha Ltd.",
      lines: [
        {
          lineNumber: 1,
          description: "USB keyboard",
          poNumber: "0100012",
          poLineNumber: 1,
          doNumber: null,
          quantity: "4",
          unitPrice: "20.00",
          lineAmount: "82.40",
        },
      ],
    });
    const blankLine = changes(ORIGINAL, ORIGINAL.header, [...ORIGINAL.lines, emptyLine(ORIGINAL.lines)]);
    expect(blankLine.lines?.[1]).toEqual({
      lineNumber: 2,
      description: null,
      poNumber: null,
      poLineNumber: null,
      doNumber: null,
    });
  });

  it("sends the DO number of a line, or null when it is cleared", () => {
    const body = changes(ORIGINAL, ORIGINAL.header, [{ ...LINE, doNumber: " DO-7 " }]);
    expect(body.lines?.[0]).toMatchObject({ doNumber: "DO-7" });
    const cleared = changes({ ...ORIGINAL, lines: [{ ...LINE, doNumber: "DO-7" }] }, ORIGINAL.header, [LINE]);
    expect(cleared.lines?.[0]).toMatchObject({ doNumber: null });
  });

  it("accepts valid values", () => {
    expect(validate(ORIGINAL.header, ORIGINAL.header, ORIGINAL.lines)).toEqual([]);
  });

  it("explains invalid values", () => {
    const header = {
      ...ORIGINAL.header,
      vendorCode: "",
      invoiceNumber: "N".repeat(51),
      totalAmount: "1.234",
    };
    const lines = [
      {
        ...LINE,
        poNumber: "123",
        poLineNumber: "0",
        doNumber: "D".repeat(51),
        quantity: "1.2345",
        unitPrice: "1.00001",
        lineAmount: "x",
      },
      { ...LINE },
    ];
    expect(validate(ORIGINAL.header, header, lines)).toEqual([
      "Vendor code cannot be emptied.",
      "Invoice number is longer than 50 characters.",
      "Total (USD) must be an amount with up to 2 decimals.",
      "Line numbers must be unique whole numbers from 1.",
      "Line 1: the PO number has 7 digits.",
      "Line 1: the PO line is a whole number from 1.",
      "Line 1: the DO number is longer than 50 characters.",
      "Line 1: the quantity has up to 3 decimals.",
      "Line 1: the unit price has up to 4 decimals.",
      "Line 1: the line amount has up to 2 decimals.",
    ]);
    expect(validate(ORIGINAL.header, ORIGINAL.header, [])).toContain("Keep at least one line.");
    expect(validate(ORIGINAL.header, ORIGINAL.header, [{ ...LINE, lineNumber: "" }])).toEqual([
      "Line numbers must be unique whole numbers from 1.",
    ]);
  });
});
