// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The values of a structure the server computes (WF-IHM-0030). Whether a cell is computed is read
 * node by node: a field no entry writes — the amounts, the float — is computed in every row that
 * bears it, and a field an entry writes is computed where the node names it among its computed
 * fields (`computed_fields`) — the dates of a task in automatic mode; the dates, the duration and
 * the progress of a summary; the figures of a provision —, never deduced from the mode nor from
 * the nature of the node.
 *
 * What a value depends on, which the refusal of an entry names, is the server's to say: each cell
 * names the field of the contract it shows, and the refusal asks the server about it
 * (`getComputedValueDependencies`). Nothing here reads a rule of the core.
 */
import type { components } from "@/api/generated/schema";

import type { ComputedCells } from "./columns";
import type { GridNode } from "./nodes";

/** A field of a node that an entry writes and the server may compute for this node alone. */
type ComputedField = components["schemas"]["ComputedField"];

/** An amount of a node, which the server computes for a task as for a line. */
type Amount = "budgeted_amount" | "reestimated_amount";

/**
 * The cells of a field an entry writes, computed in the rows whose node names it among its
 * computed fields.
 */
export function computedWhereNamed(field: ComputedField): ComputedCells<GridNode> {
  return {
    whole: false,
    in: (node) => node.computed_fields.includes(field),
    field: () => field,
  };
}

/**
 * The cells of an amount, computed in every row: the field of the facet the row bears — the
 * task's, or the line's.
 */
export function computedAmount(amount: Amount): ComputedCells<GridNode> {
  return {
    whole: true,
    in: () => true,
    field: (node) => (node.kind === "task" ? `task.${amount}` : `estimate_line.${amount}`),
  };
}

/** The cells of the total float, computed in every task. */
export const COMPUTED_FLOAT: ComputedCells<GridNode> = {
  whole: true,
  in: (node) => node.task !== undefined && node.task !== null,
  field: () => "task.total_float",
};

/**
 * The cells of the amount corrected for inflation, computed in every line: a task bears none
 * (WF-DEV-0040, WF-DEV-0050).
 */
export const COMPUTED_INFLATED: ComputedCells<GridNode> = {
  whole: true,
  in: (node) => node.estimate_line !== undefined && node.estimate_line !== null,
  field: () => "estimate_line.inflated_amount",
};
