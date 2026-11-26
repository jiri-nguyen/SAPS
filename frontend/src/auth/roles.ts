import type { Role } from "../api/session";

export const ROLE_LABEL: Record<Role, string> = {
  ACCOUNTING_MEMBER: "Accounting Member",
  ACCOUNTING_MANAGER: "Accounting Manager",
};

export interface MenuItem {
  id: string;
  label: string;
}

/** Menu items allowed per role (SAPS-27 BR-10); the screens come with their features. */
export const MENU_BY_ROLE: Record<Role, readonly [MenuItem, ...MenuItem[]]> = {
  ACCOUNTING_MEMBER: [
    { id: "upload", label: "Upload invoices" },
    { id: "exceptions", label: "Exception queue" },
    { id: "review", label: "Review queue" },
    { id: "invoices", label: "All invoices" },
  ],
  ACCOUNTING_MANAGER: [
    { id: "approvals", label: "Approval queue" },
    { id: "exceptions", label: "Exception queue" }, // read-only; a manager may release any claim (DEC-036)
    { id: "invoices", label: "All invoices" },
    { id: "processing-calendar", label: "Processing calendar" },
    { id: "matching-settings", label: "Matching settings" },
  ],
};

/** Only Accounting Members claim, correct, accept or reject invoices in the exception queue (SAPS-20 BR-02). */
export function canHandleExceptions(role: Role): boolean {
  return role === "ACCOUNTING_MEMBER";
}
