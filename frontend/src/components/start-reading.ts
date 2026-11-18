// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A read a page starts without awaiting it, for a part of the screen that streams apart
 * (`Streamed`, US-2290).
 */

/**
 * The read, observed so that a page which leaves before showing it — not found, a refusal of
 * another read — does not leave a rejection unhandled; whoever shows it still gets the rejection.
 */
export function startReading<Value>(read: Promise<Value>): Promise<Value> {
  read.catch(() => undefined);
  return read;
}
