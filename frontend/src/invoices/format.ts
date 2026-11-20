import type { components } from "../api/schema";

type InvoiceStatus = components["schemas"]["InvoiceStatus"];
export type ExceptionCode = components["schemas"]["ExceptionCode"];

export const STATUS_LABEL: Record<InvoiceStatus, string> = {
  UPLOADED: "Uploaded",
  MATCHING: "Matching",
  EXCEPTION: "Exception",
  PENDING_APPROVAL: "Pending approval",
  PENDING_REVIEW: "Pending review",
  COMPLETED: "Completed",
  REJECTED: "Rejected",
};

/** Exception types of the PoC (DEC-033). */
export const EXCEPTION_TITLE: Record<ExceptionCode, string> = {
  EX1: "Invoice unreadable",
  EX2: "Non-PO invoice",
  EX3: "Invalid or missing PO number",
  EX4: "PO or PO line not found",
  EX5: "Trade and non-trade POs",
  EX6: "Unit price outside tolerance",
  EX7: "Quantity above expected",
  EX8: "Missing goods receipt",
  EX9: "Duplicate invoice",
  EX10: "Vendor does not match the PO",
};

/** SAPS-20 BR-06 (DEC-035): the others need corrected data or a rejection. */
const ACCEPTABLE_AS_IS: ReadonlySet<ExceptionCode> = new Set(["EX2", "EX6", "EX7", "EX9"]);

export function refusedCodes(codes: readonly ExceptionCode[]): ExceptionCode[] {
  return [...new Set(codes.filter((code) => !ACCEPTABLE_AS_IS.has(code)))].sort(
    (a, b) => Number(a.slice(2)) - Number(b.slice(2)),
  );
}

/** A decimal string for display: trailing zeros removed, at least `minPlaces` decimals ("20.6000" → "20.60"). */
export function decimal(value: string | null | undefined, minPlaces = 2): string {
  if (value === null || value === undefined) return "—";
  const [whole = "", fraction = ""] = value.split(".");
  const trimmed = fraction.replace(/0+$/, "").padEnd(minPlaces, "0");
  return trimmed ? `${whole}.${trimmed}` : whole;
}

/** ISO timestamp as "2026-12-15 09:30 UTC" (the same for every viewer). */
export function timestamp(iso: string): string {
  return `${iso.slice(0, 10)} ${iso.slice(11, 16)} UTC`;
}

export function text(value: string | number | null | undefined): string {
  return value === null || value === undefined || value === "" ? "—" : String(value);
}
