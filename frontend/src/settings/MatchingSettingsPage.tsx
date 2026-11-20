import { type FormEvent, useEffect, useState } from "react";

import { ApiError } from "../api/client";
import type { MatchingSettings, SettingsApi } from "../api/settings";
import { errorMessage } from "../invoices/errors";
import { decimal, timestamp } from "../invoices/format";

type Field = "priceToleranceUsd" | "approvalThresholdUsd";

// SAPS-28 BR-03 (DEC-045): 0 USD or more; the tolerance has up to 4 decimals, the threshold up to 2.
const RULES: Record<Field, { pattern: RegExp; message: string }> = {
  priceToleranceUsd: {
    pattern: /^\d{1,14}(\.\d{1,4})?$/,
    message: "Enter the price tolerance as a number of 0 or more with up to 4 decimals.",
  },
  approvalThresholdUsd: {
    pattern: /^\d{1,16}(\.\d{1,2})?$/,
    message: "Enter the approval threshold as a number of 0 or more with up to 2 decimals.",
  },
};

type Errors = Partial<Record<Field, string>>;

function shown(settings: MatchingSettings) {
  return {
    priceToleranceUsd: decimal(settings.priceToleranceUsd),
    approvalThresholdUsd: decimal(settings.approvalThresholdUsd),
  };
}

/** The Matching settings screen of the Accounting Manager (SAPS-28, UC-07). */
export function MatchingSettingsPage({ api }: { api: SettingsApi }) {
  const [settings, setSettings] = useState<MatchingSettings | null>(null);
  const [values, setValues] = useState({ priceToleranceUsd: "", approvalThresholdUsd: "" });
  const [fieldErrors, setFieldErrors] = useState<Errors>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    api.get().then(
      (loaded) => {
        if (!active) return;
        setSettings(loaded);
        setValues(shown(loaded));
      },
      (caught: unknown) => {
        if (active) setError(errorMessage(caught));
      },
    );
    return () => {
      active = false;
    };
  }, [api]);

  function change(field: Field, value: string) {
    setValues((current) => ({ ...current, [field]: value }));
    setSaved(false);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSaved(false);
    const trimmed = {
      priceToleranceUsd: values.priceToleranceUsd.trim(),
      approvalThresholdUsd: values.approvalThresholdUsd.trim(),
    };
    const invalid: Errors = {};
    for (const field of Object.keys(RULES) as Field[]) {
      if (!RULES[field].pattern.test(trimmed[field])) invalid[field] = RULES[field].message;
    }
    setFieldErrors(invalid);
    if (Object.keys(invalid).length > 0) return;

    setBusy(true);
    try {
      const result = await api.update(trimmed);
      setSettings(result);
      setValues(shown(result));
      setSaved(true);
    } catch (caught) {
      const named: Errors = {};
      if (caught instanceof ApiError) {
        for (const item of caught.problem?.errors ?? []) {
          if (item.field === "priceToleranceUsd" || item.field === "approvalThresholdUsd") {
            named[item.field] = item.message ?? "The value is not valid.";
          }
        }
      }
      if (Object.keys(named).length > 0) setFieldErrors(named);
      else setError(errorMessage(caught));
    } finally {
      setBusy(false);
    }
  }

  if (settings === null) {
    return error !== null ? (
      <p role="alert" className="banner error">
        {error}
      </p>
    ) : (
      <p className="muted">Loading…</p>
    );
  }

  return (
    <section className="stack" aria-label="Matching settings">
      <p className="muted">
        Last changed by {settings.updatedBy} on {timestamp(settings.updatedAt)}.
      </p>
      {error !== null && (
        <p role="alert" className="banner error">
          {error}
        </p>
      )}
      {saved && (
        <p role="status" className="banner success">
          Saved. The new values apply to the next matching runs.
        </p>
      )}
      <form className="stack settings-form" aria-label="Change matching settings" onSubmit={save} noValidate>
        <label>
          Price tolerance (USD)
          <input
            inputMode="decimal"
            value={values.priceToleranceUsd}
            aria-invalid={fieldErrors.priceToleranceUsd !== undefined}
            aria-describedby="tolerance-help"
            onChange={(e) => change("priceToleranceUsd", e.target.value)}
          />
        </label>
        <p id="tolerance-help" className="hint">
          The largest difference between the invoice unit price and the PO price that still matches. 0 means
          the prices must be equal.
        </p>
        {fieldErrors.priceToleranceUsd !== undefined && (
          <p role="alert" className="field-error">
            {fieldErrors.priceToleranceUsd}
          </p>
        )}
        <label>
          Approval threshold (USD)
          <input
            inputMode="decimal"
            value={values.approvalThresholdUsd}
            aria-invalid={fieldErrors.approvalThresholdUsd !== undefined}
            aria-describedby="threshold-help"
            onChange={(e) => change("approvalThresholdUsd", e.target.value)}
          />
        </label>
        <p id="threshold-help" className="hint">
          Invoices with a total above this amount need approval by an Accounting Manager. 0 means every
          invoice with a total above 0 needs approval.
        </p>
        {fieldErrors.approvalThresholdUsd !== undefined && (
          <p role="alert" className="field-error">
            {fieldErrors.approvalThresholdUsd}
          </p>
        )}
        <p className="hint">Invoices that were already processed keep the values they were processed with.</p>
        <div className="actions">
          <button type="submit" disabled={busy}>
            Save settings
          </button>
        </div>
      </form>
    </section>
  );
}
