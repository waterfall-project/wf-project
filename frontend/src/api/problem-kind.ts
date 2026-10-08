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

/** What a refusal of a status asks of the screen: `refused` for any status but these. */
export function kindOf(status: number): ProblemKind {
  return KIND_BY_STATUS[status] ?? "refused";
}
