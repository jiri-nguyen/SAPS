import { ApiError } from "../api/client";

/** The problem detail of an API error, or a general message (network and other errors). */
export function errorMessage(caught: unknown): string {
  if (caught instanceof ApiError && caught.status !== 0) return caught.message;
  return "Something went wrong. Check the connection and try again.";
}

export function isStale(caught: unknown): boolean {
  return caught instanceof ApiError && caught.status === 412;
}
