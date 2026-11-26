import type { Invoice } from "../api/invoices";
import type { InvoiceLineUpdate, InvoiceUpdate } from "../api/exceptions";
import { decimal } from "./format";

/** The edit form's values, as text (SAPS-20 BR-04). */
export const HEADER_FIELDS = [
  { key: "vendorCode", label: "Vendor code", max: 20 },
  { key: "vendorName", label: "Vendor name", max: 200 },
  { key: "invoiceNumber", label: "Invoice number", max: 50 },
  { key: "invoiceDate", label: "Invoice date", max: 10 },
  { key: "subtotalAmount", label: "Subtotal (USD)", max: 20 },
  { key: "taxAmount", label: "Tax (USD)", max: 20 },
  { key: "totalAmount", label: "Total (USD)", max: 20 },
] as const;

export type HeaderKey = (typeof HEADER_FIELDS)[number]["key"];
export type HeaderValues = Record<HeaderKey, string>;

export interface LineValues {
  lineNumber: string;
  description: string;
  poNumber: string;
  poLineNumber: string;
  doNumber: string;
  quantity: string;
  unitPrice: string;
  lineAmount: string;
}

const AMOUNT = /^-?\d{1,16}(\.\d{1,2})?$/;
const UNIT_PRICE = /^-?\d{1,14}(\.\d{1,4})?$/;
const QUANTITY = /^\d{1,15}(\.\d{1,3})?$/;
const PO_NUMBER = /^\d{7}$/;
const DO_NUMBER_MAX = 50;
const POSITIVE = /^[1-9]\d*$/;
const AMOUNT_KEYS: readonly HeaderKey[] = ["subtotalAmount", "taxAmount", "totalAmount"];

const plain = (value: string | null | undefined) => value ?? "";
const amount = (value: string | null | undefined) => (value == null ? "" : decimal(value));

export function headerOf(invoice: Invoice): HeaderValues {
  return {
    vendorCode: plain(invoice.vendorCode),
    vendorName: plain(invoice.vendorName),
    invoiceNumber: plain(invoice.invoiceNumber),
    invoiceDate: plain(invoice.invoiceDate),
    subtotalAmount: amount(invoice.subtotalAmount),
    taxAmount: amount(invoice.taxAmount),
    totalAmount: amount(invoice.totalAmount),
  };
}

export function linesOf(invoice: Invoice): LineValues[] {
  return invoice.lines.map((line) => ({
    lineNumber: String(line.lineNumber),
    description: plain(line.description),
    poNumber: plain(line.poNumber),
    poLineNumber: line.poLineNumber == null ? "" : String(line.poLineNumber),
    doNumber: plain(line.doNumber),
    quantity: line.quantity == null ? "" : decimal(line.quantity, 0),
    unitPrice: amount(line.unitPrice),
    lineAmount: amount(line.lineAmount),
  }));
}

export function emptyLine(lines: readonly LineValues[]): LineValues {
  const highest = Math.max(0, ...lines.map((line) => Number(line.lineNumber) || 0));
  return {
    lineNumber: String(highest + 1),
    description: "",
    poNumber: "",
    poLineNumber: "",
    doNumber: "",
    quantity: "",
    unitPrice: "",
    lineAmount: "",
  };
}

function lineUpdate(line: LineValues): InvoiceLineUpdate {
  const value = (text: string) => text.trim();
  return {
    lineNumber: Number(line.lineNumber),
    description: value(line.description) || null,
    poNumber: value(line.poNumber) || null,
    poLineNumber: value(line.poLineNumber) ? Number(line.poLineNumber) : null,
    doNumber: value(line.doNumber) || null,
    ...(value(line.quantity) ? { quantity: value(line.quantity) } : {}),
    ...(value(line.unitPrice) ? { unitPrice: value(line.unitPrice) } : {}),
    ...(value(line.lineAmount) ? { lineAmount: value(line.lineAmount) } : {}),
  };
}

/** Client checks that mirror the contract, so mistakes show before saving; the SAPS API checks again. */
export function validate(
  original: HeaderValues,
  header: HeaderValues,
  lines: readonly LineValues[],
): string[] {
  const errors: string[] = [];
  for (const field of HEADER_FIELDS) {
    const value = header[field.key].trim();
    if (value === "" && original[field.key] !== "") errors.push(`${field.label} cannot be emptied.`);
    if (value.length > field.max) errors.push(`${field.label} is longer than ${field.max} characters.`);
  }
  for (const key of AMOUNT_KEYS) {
    const value = header[key].trim();
    if (value !== "" && !AMOUNT.test(value))
      errors.push(`${labelOf(key)} must be an amount with up to 2 decimals.`);
  }
  if (lines.length === 0) errors.push("Keep at least one line.");
  const numbers = lines.map((line) => line.lineNumber.trim());
  if (numbers.some((n) => !POSITIVE.test(n)) || new Set(numbers).size !== numbers.length) {
    errors.push("Line numbers must be unique whole numbers from 1.");
  }
  lines.forEach((line) => {
    const name = `Line ${line.lineNumber || "?"}`;
    if (line.poNumber.trim() && !PO_NUMBER.test(line.poNumber.trim()))
      errors.push(`${name}: the PO number has 7 digits.`);
    if (line.poLineNumber.trim() && !POSITIVE.test(line.poLineNumber.trim()))
      errors.push(`${name}: the PO line is a whole number from 1.`);
    if (line.doNumber.trim().length > DO_NUMBER_MAX)
      errors.push(`${name}: the DO number is longer than ${DO_NUMBER_MAX} characters.`);
    if (line.quantity.trim() && !QUANTITY.test(line.quantity.trim()))
      errors.push(`${name}: the quantity has up to 3 decimals.`);
    if (line.unitPrice.trim() && !UNIT_PRICE.test(line.unitPrice.trim()))
      errors.push(`${name}: the unit price has up to 4 decimals.`);
    if (line.lineAmount.trim() && !AMOUNT.test(line.lineAmount.trim()))
      errors.push(`${name}: the line amount has up to 2 decimals.`);
  });
  return errors;
}

function labelOf(key: HeaderKey): string {
  return HEADER_FIELDS.find((field) => field.key === key)?.label ?? key;
}

/** Only changed header fields; `lines` (all of them) only when a line changed (SAPS-20 BR-04, EC-08). */
export function changes(
  original: { header: HeaderValues; lines: readonly LineValues[] },
  header: HeaderValues,
  lines: readonly LineValues[],
): InvoiceUpdate {
  const body: InvoiceUpdate = {};
  for (const field of HEADER_FIELDS) {
    const value = header[field.key].trim();
    if (value !== "" && value !== original.header[field.key]) body[field.key] = value;
  }
  const before = JSON.stringify(original.lines.map(lineUpdate));
  const after = lines.map(lineUpdate);
  if (JSON.stringify(after) !== before) body.lines = after;
  return body;
}
