// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a refusal of the API asks of the screen, by the status that carries it: the one table the
 * decoder (`problem.ts`, which re-exports it) and the refusal of a result carried back in an
 * address (`result-refusal.ts`) read. A module of its own, which reads nothing of the server: the
 * decoder imports the client of the API, which a browser never loads.
 */

/** What a refusal of the API asks of the screen, by the status that carries it. */
export type ProblemKind = "refused" | "stale" | "conflict" | "signed_out";

/** The reaction a status asks for; any other refusal is rendered as it is. */
const KIND_BY_STATUS: Readonly<Record<number, ProblemKind>> = {
  401: "signed_out",
  409: "conflict",
  412: "stale",
};

/** The 401 that refuse the account itself, whatever its session: deactivated, or not admitted. */
const ACCOUNT_REFUSALS: ReadonlySet<unknown> = new Set([
  "ACCOUNT_DEACTIVATED",
  "ACCOUNT_NOT_ADMITTED",
]);

/**
 * Whether a 401 refuses the account itself rather than its session — deactivated
 * (`ACCOUNT_DEACTIVATED`), or one Waterfall does not admit (`ACCOUNT_NOT_ADMITTED`, #664): leading
 * it back to the sign-in page would loop, the identity provider signing it in again to the same
 * refusal. The screen says it instead.
 */
export function isAccountRefusal(status: number, code: unknown): boolean {
  return status === 401 && ACCOUNT_REFUSALS.has(code);
}

/**
 * What a refusal of a status asks of the screen: `refused` for any status but these — and for a
 * 401 that refuses the account, which is no session to open again (`isAccountRefusal`).
 */
export function kindOf(status: number, code?: string): ProblemKind {
  return isAccountRefusal(status, code) ? "refused" : (KIND_BY_STATUS[status] ?? "refused");
}
