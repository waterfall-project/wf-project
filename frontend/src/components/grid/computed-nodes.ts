// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The values of a structure the server computes (WF-IHM-0030), and what they depend on. Whether a
 * cell is computed is read node by node: a field no entry writes — the amounts, the float — is
 * computed in every row that bears it, and a field an entry writes is computed where the node
 * names it among its computed fields (`computed_fields`) — the dates of a task in automatic mode;
 * the dates, the duration and the progress of a summary; the figures of a provision —, never
 * deduced from the mode nor from the nature of the node.
 *
 * What a value depends on is what the refusal of an entry names. The contract does not say it: it
 * is read here from what the row bears — its kind, its flags, its mode —, after the rules the
 * contract describes (#168): the subordinates of a summary, the links of a task in automatic mode,
 * the effort and the rate of a line of labour, the risk of a provision. What those rules do not
 * cover — a duration or a progress computed out of a summary, a figure out of a provision, a mode
 * the grid does not read —, the refusal says it cannot tell. The subordinates are those of the answer, found by its order and the levels of its
 * rows: the answer is depth first, a sort ordering siblings among themselves without undoing the
 * tree, so the direct subordinates of a row are the rows one level down that follow it, before
 * the next row of its level or above. A search keeps the ancestors of what it retains and leaves
 * the rest out: what it left out is not named.
 */
import type { components } from "@/api/generated/schema";

import type { ComputedCells, Dependency, DependencyReason } from "./columns";
import type { GridNode } from "./nodes";
import { type RowNature, rowNature } from "./row-nature";

/** A field of a node that an entry writes and the server may compute for this node alone. */
type ComputedField = components["schemas"]["ComputedField"];

/** The scheduling mode of a task (WF-PLA-0020). */
type SchedulingMode = components["schemas"]["SchedulingMode"];

/**
 * What a cell of a structure shows that the server computes: the dates, the duration or the
 * progress of a task, a figure of a line — its quantity, its effort, its unit disbursement —, one
 * of its two amounts, the float of a task.
 */
export type NodeValue =
  "dates" | "duration" | "progress" | "figure" | "budgeted" | "reestimated" | "float";

/** A node as the refusal reads it: what every grid reads, and its mode where its grid reads it. */
type DependencyNode = GridNode & {
  readonly task?: { readonly scheduling_mode?: SchedulingMode } | null;
};

/**
 * The indices of the direct subordinates of the row at `index` in the rows of an answer — of a
 * kind, or all of them —: the rows one level down that follow it, until the next of its level.
 */
export function subordinates(
  rows: readonly Pick<GridNode, "level" | "kind">[],
  index: number,
  kind?: GridNode["kind"],
): number[] {
  const level = rows[index]?.level ?? Number.POSITIVE_INFINITY;
  const found: number[] = [];
  for (let next = index + 1; next < rows.length; next += 1) {
    const row = rows[next];
    if (row === undefined || row.level <= level) {
      break;
    }
    if (row.level === level + 1 && (kind === undefined || row.kind === kind)) {
      found.push(next);
    }
  }
  return found;
}

/** Why the server computes the amount of a node, by its nature: a nature added without one breaks the typing. */
const AMOUNT_REASONS = {
  summary: "taskAmount",
  task: "taskAmount",
  milestone: "taskAmount",
  labour: "labour",
  disbursement: "disbursement",
  provision: "provision",
} as const satisfies Readonly<Record<RowNature, DependencyReason>>;

/**
 * What an amount of a node depends on: the rule of its nature, and for a task what it bears — its
 * subordinates and its lines.
 */
function amountDependency(rows: readonly GridNode[], index: number, node: GridNode): Dependency {
  return {
    reasons: [AMOUNT_REASONS[rowNature(node)]],
    rows: node.kind === "task" ? subordinates(rows, index) : null,
  };
}

/**
 * What a value of the schedule of a task depends on: the subordinates of a summary, whatever the
 * value; the duration, the links and the calendar of the dates of a task in automatic mode. Any
 * other case the contract does not describe, and the refusal says it cannot tell (#168).
 */
function scheduleDependency(
  rows: readonly GridNode[],
  index: number,
  node: DependencyNode,
  value: NodeValue,
): Dependency {
  if (node.task?.is_summary === true) {
    return { reasons: ["summary"], rows: subordinates(rows, index, "task") };
  }
  const automatic = node.task?.scheduling_mode === "automatic";
  return { reasons: [value === "dates" && automatic ? "automatic" : "unknown"], rows: null };
}

/**
 * What the float of a task depends on: its earliest and latest dates in automatic mode; a task in
 * manual mode bears none (WF-PLA-0100). A grid that does not read the mode cannot tell.
 */
function floatDependency(node: DependencyNode): Dependency {
  const reasons = {
    automatic: "float",
    manual: "manualFloat",
    unread: "unknown",
  } as const satisfies Readonly<Record<SchedulingMode | "unread", DependencyReason>>;
  return { reasons: [reasons[node.task?.scheduling_mode ?? "unread"]], rows: null };
}

/**
 * What a value of the node at `index` among the rows of an answer depends on, read from what its
 * row bears — its kind, its flags, its mode —, after the rules the contract describes (#168).
 */
export function nodeDependency(
  rows: readonly DependencyNode[],
  index: number,
  value: NodeValue,
): Dependency {
  const node = rows[index];
  if (node === undefined) {
    return { reasons: [], rows: null };
  }
  switch (value) {
    case "dates":
    case "duration":
    case "progress":
      return scheduleDependency(rows, index, node, value);
    case "figure":
      return { reasons: [rowNature(node) === "provision" ? "provision" : "unknown"], rows: null };
    case "float":
      return floatDependency(node);
    case "budgeted":
    case "reestimated": {
      const amount = amountDependency(rows, index, node);
      return { ...amount, reasons: [...amount.reasons, value] };
    }
  }
}

/**
 * The cells of a field an entry writes, computed in the rows whose node names it among its
 * computed fields.
 */
export function computedWhereNamed(
  field: ComputedField,
  value: NodeValue,
): ComputedCells<GridNode> {
  return {
    whole: false,
    in: (node) => node.computed_fields.includes(field),
    dependsOn: (rows, index) => nodeDependency(rows, index, value),
  };
}

/**
 * The cells of a field no entry writes, computed in every row that bears it: the amounts in each
 * task and line, the float in each task.
 */
export function computedAlways(value: NodeValue): ComputedCells<GridNode> {
  return {
    whole: true,
    in: value === "float" ? (node) => node.task !== undefined && node.task !== null : () => true,
    dependsOn: (rows, index) => nodeDependency(rows, index, value),
  };
}
