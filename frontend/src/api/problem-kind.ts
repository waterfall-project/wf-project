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

/**
 * Whether a 401 says the account is deactivated (`ACCOUNT_DEACTIVATED`) rather than no session:
 * leading it back to the sign-in page would loop, the identity provider signing it in again to
 * the same refusal. The screen says it instead.
 */
export function isDeactivation(status: number, code: unknown): boolean {
  return status === 401 && code === "ACCOUNT_DEACTIVATED";
}

/**
 * What a refusal of a status asks of the screen: `refused` for any status but these — and for a
 * 401 that names the deactivated account, which is no session to open again (`isDeactivation`).
 */
export function kindOf(status: number, code?: string): ProblemKind {
  return isDeactivation(status, code) ? "refused" : (KIND_BY_STATUS[status] ?? "refused");
}
