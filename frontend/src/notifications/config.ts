export const DEFAULT_POLL_SECONDS = 15;

/** Polling interval in ms from `VITE_NOTIFICATION_POLL_SECONDS` (set at build time, SAPS-24 §3.8); 15 s by default. */
export function pollIntervalMs(
  raw: string | undefined = import.meta.env.VITE_NOTIFICATION_POLL_SECONDS,
): number {
  const seconds = Number(raw);
  return (Number.isFinite(seconds) && seconds > 0 ? seconds : DEFAULT_POLL_SECONDS) * 1000;
}
