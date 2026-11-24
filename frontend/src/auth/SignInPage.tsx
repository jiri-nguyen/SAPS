import { type FormEvent, useEffect, useState } from "react";

import { browser } from "./browser";

const SIGN_IN_URL = "/v1/session/sign-in";
const REASON_PARAM = "signIn";

/** One message per reason code of a refused sign-in (SAPS-44 §3.1). */
const MESSAGES: Record<string, string> = {
  cancelled: "Sign-in was cancelled. Try again.",
  expired: "Your sign-in took too long or was started in another tab. Try again.",
  no_company: "Your account is not assigned to exactly one company. Ask your administrator.",
  wrong_domain: "Your e-mail address does not belong to your company. Ask your administrator.",
  no_role: "Your account needs exactly one SAPS role. Ask your administrator.",
  unavailable: "Sign-in is not available at the moment. Try again later.",
};

function reasonInUrl(): string | null {
  return new URLSearchParams(window.location.search).get(REASON_PARAM);
}

function messageFor(reason: string): string {
  return MESSAGES[reason] ?? "Sign-in is not available at the moment. Try again later.";
}

/** Sign-in through the company account in Keycloak (SAPS-44); the SAPS API runs the OpenID Connect flow. */
export function SignInPage() {
  const [reason] = useState(reasonInUrl);

  useEffect(() => {
    // Shown once: a reload or a bookmark does not repeat the message.
    const params = new URLSearchParams(window.location.search);
    if (!params.has(REASON_PARAM)) return;
    params.delete(REASON_PARAM);
    const query = params.toString();
    const url = `${window.location.pathname}${query ? `?${query}` : ""}${window.location.hash}`;
    window.history.replaceState(window.history.state, "", url);
  }, []);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const returnTo = `${window.location.pathname}${window.location.hash}`;
    browser.assign(`${SIGN_IN_URL}?returnTo=${encodeURIComponent(returnTo)}`);
  }

  return (
    <main className="sign-in">
      <h1>Smart-AP-Suite</h1>
      <form onSubmit={submit} aria-label="Sign in">
        {reason !== null && <p role="alert">{messageFor(reason)}</p>}
        <button type="submit">Sign in with your company account</button>
      </form>
    </main>
  );
}
