// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The body of the answer 200 of an operation of the contract, as the generated client types it: the
 * paths that read the API by hand cast to it what they read, rather than to an envelope written out.
 */
import type { operations } from "../src/api/generated/schema";

export type Answer<Operation extends keyof operations> = operations[Operation] extends {
  responses: { 200: { content: { "application/json": infer Body } } };
}
  ? Body
  : never;
