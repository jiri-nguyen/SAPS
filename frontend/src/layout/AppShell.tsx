import { type ReactNode, useState } from "react";

import type { UserAccount } from "../api/session";
import { MENU_BY_ROLE, ROLE_LABEL } from "../auth/roles";
import { useSession } from "../auth/session-context";

export function AppShell({ user, footer }: { user: UserAccount; footer?: ReactNode }) {
  const { signOut } = useSession();
  const menu = MENU_BY_ROLE[user.role];
  const [selected, setSelected] = useState<string>();
  const current = menu.find((item) => item.id === selected) ?? menu[0];

  return (
    <>
      <header>
        <strong>Smart-AP-Suite</strong>
        <span data-testid="signed-in-user">
          {user.displayName} ({ROLE_LABEL[user.role]})
        </span>
        <button type="button" onClick={() => void signOut()}>
          Sign out
        </button>
      </header>
      <nav aria-label="Main menu">
        <ul>
          {menu.map((item) => (
            <li key={item.id}>
              <button
                type="button"
                aria-current={item.id === current.id ? "page" : undefined}
                onClick={() => setSelected(item.id)}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      </nav>
      <main>
        <h1>{current.label}</h1>
        <p>This screen is not available yet.</p>
      </main>
      {footer}
    </>
  );
}
