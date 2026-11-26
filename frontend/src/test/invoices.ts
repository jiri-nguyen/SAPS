import { vi } from "vitest";

import type { ExceptionApi, InvoiceSummary, Versioned } from "../api/exceptions";
import type { Invoice } from "../api/invoices";
import type { UserAccount } from "../api/session";

export const MEMBER: UserAccount = {
  id: "u-member",
  username: "member1",
  displayName: "Accounting Member 1",
  role: "ACCOUNTING_MEMBER",
  companyName: "Demo Vietnam",
};
export const OTHER: UserAccount = {
  id: "u-other",
  username: "member2",
  displayName: "Accounting Member 2",
  role: "ACCOUNTING_MEMBER",
  companyName: "Demo Vietnam",
};
export const MANAGER: UserAccount = {
  id: "u-manager",
  username: "manager1",
  displayName: "Accounting Manager 1",
  role: "ACCOUNTING_MANAGER",
  companyName: "Demo Vietnam",
};

const ref = (user: UserAccount) => ({ id: user.id, displayName: user.displayName });

/** DS-12: one line, unit price 20.60 against the PO price 20.00 (EX6). */
export function invoiceFixture(overrides: Partial<Invoice> = {}): Invoice {
  return {
    id: "inv-12",
    status: "EXCEPTION",
    invoiceType: "TRADE_PO",
    vendorCode: "V001",
    vendorName: "Alpha Office Supplies Co.",
    invoiceNumber: "AOS-2026-1013",
    invoiceDate: "2026-12-09",
    currency: "USD",
    subtotalAmount: "82.40",
    taxAmount: "8.24",
    totalAmount: "90.64",
    requiresApproval: false,
    priceToleranceApplied: "0.5000",
    approvalThresholdApplied: "300.00",
    assignedTo: null,
    uploadedBy: ref(MEMBER),
    source: { channel: "UPLOAD" },
    file: { name: "ds-12.pdf", contentType: "application/pdf", sizeBytes: 2000, sha256: "a".repeat(64) },
    rejectedReason: null,
    lines: [
      {
        id: "line-1",
        lineNumber: 1,
        description: "USB keyboard",
        poNumber: "0100012",
        poLineNumber: 1,
        quantity: "4.000",
        unitPrice: "20.6000",
        lineAmount: "82.40",
        matchStatus: "MISMATCH",
        poUnitPrice: "20.0000",
        expectedQuantity: "4.000",
      },
    ],
    exceptions: [
      {
        id: "ex-1",
        code: "EX6",
        message:
          "Line 1: unit price 20.6 USD differs from the PO unit price 20 USD by 0.6 USD (tolerance 0.5 USD).",
        status: "OPEN",
        invoiceLineId: "line-1",
        resolvedBy: null,
        resolvedAt: null,
        createdAt: "2026-12-15T09:00:00Z",
      },
    ],
    approval: null,
    createdAt: "2026-12-15T09:00:00Z",
    updatedAt: "2026-12-15T09:00:00Z",
    ...overrides,
  };
}

export function claimedBy(user: UserAccount, overrides: Partial<Invoice> = {}): Invoice {
  return invoiceFixture({ assignedTo: ref(user), ...overrides });
}

export function versioned(invoice: Invoice, etag = 'W/"1"'): Versioned {
  return { invoice, etag };
}

export function summary(overrides: Partial<InvoiceSummary> = {}): InvoiceSummary {
  return {
    id: "inv-12",
    status: "EXCEPTION",
    invoiceType: "TRADE_PO",
    vendorName: "Alpha Office Supplies Co.",
    invoiceNumber: "AOS-2026-1013",
    totalAmount: "90.64",
    currency: "USD",
    openExceptionCodes: ["EX6"],
    assignedTo: null,
    updatedAt: "2026-12-15T09:00:00Z",
    invoiceDate: "2026-12-09",
    channel: "UPLOAD",
    uploadedAt: "2026-12-15T08:30:00Z",
    ...overrides,
  };
}

export function fakeExceptionApi(overrides: Partial<ExceptionApi> = {}): ExceptionApi {
  return {
    getVersioned: vi.fn().mockResolvedValue(versioned(invoiceFixture())),
    list: vi.fn().mockResolvedValue({ items: [], nextPageToken: null }),
    claim: vi.fn().mockResolvedValue(versioned(claimedBy(MEMBER))),
    releaseHold: vi.fn(),
    release: vi.fn().mockResolvedValue(undefined),
    update: vi.fn(),
    resolve: vi.fn(),
    reject: vi.fn(),
    decide: vi.fn(),
    confirm: vi.fn(),
    events: vi.fn().mockResolvedValue([]),
    fileUrl: (id: string) => `/v1/invoices/${id}/file`,
    ...overrides,
  };
}
