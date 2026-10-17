// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The codes the system gives a connection that failed for the network, which the session reads
 * alike of the realm (`provider.ts`) and of Redis (`store.ts`): a component out of reach, never a
 * defect of the front.
 */

/**
 * A connection that could not be made: refused, its host unknown, out of reach or down, its
 * network out of reach or down. Nothing left by it.
 */
export const UNMADE_CONNECTION = [
  "ECONNREFUSED",
  "ENOTFOUND",
  "EAI_AGAIN",
  "ENETUNREACH",
  "ENETDOWN",
  "EHOSTUNREACH",
  "EHOSTDOWN",
] as const;

/**
 * A connection lost once made: reset or aborted, written to once closed, its network reset, or
 * silent past its time. What was sent on it may have arrived.
 */
export const LOST_CONNECTION = [
  "ECONNRESET",
  "ECONNABORTED",
  "EPIPE",
  "ENETRESET",
  "ETIMEDOUT",
] as const;
