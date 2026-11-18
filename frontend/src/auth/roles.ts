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
  ],
  ACCOUNTING_MANAGER: [
    { id: "approvals", label: "Approval queue" },
    { id: "matching-settings", label: "Matching settings" },
  ],
};
