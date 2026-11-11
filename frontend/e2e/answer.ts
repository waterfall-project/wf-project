// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The body of the answer 200 of a read operation of the contract, as the generated client types it:
 * the paths that read the envelope of such an answer by hand cast it to `Answer<op>`. The other
 * bodies (errors, writes) stay read by `Schemas[...]`.
 */
import type { operations } from "../src/api/generated/schema";

export type Answer<Operation extends keyof operations> = operations[Operation] extends {
  responses: { 200: { content: { "application/json": infer Body } } };
}
  ? Body
  : never;
