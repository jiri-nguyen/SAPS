import { type FormEvent, useState } from "react";

import { ApiError } from "../api/client";
import { useSession } from "./session-context";

function messageFor(error: unknown): string {
  if (error instanceof ApiError && error.status === 401) return "Invalid username or password.";
  return "Sign-in failed. Please try again.";
}

export function SignInPage() {
  const { signIn } = useSession();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await signIn(username.trim(), password);
    } catch (caught) {
      setError(messageFor(caught));
      setPassword("");
      setBusy(false);
    }
  }

  return (
    <main className="sign-in">
      <h1>Smart-AP-Suite</h1>
      <form onSubmit={(event) => void submit(event)} aria-label="Sign in">
        <label>
          Username
          <input
            name="username"
            autoComplete="username"
            required
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </label>
        <label>
          Password
          <input
            name="password"
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        {error !== null && <p role="alert">{error}</p>}
        <button type="submit" disabled={busy}>
          Sign in
        </button>
      </form>
    </main>
  );
}
