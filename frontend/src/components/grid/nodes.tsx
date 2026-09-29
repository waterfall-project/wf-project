// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the grids of a structure share (EP-02, « Grille dense »): the planning and the estimate
 * read the same tree (`listNodes`), the same tasks seen from the side of time or of money
 * (§3.5.1). Both number a row as the API does, indent it by its level, mark it by the icon of
 * its nature and show its label: two configurations of one grid, which differ by their columns
 * alone — and by what they ask of the server, the planning without the lines.
 */
import type { components, operations } from "@/api/generated/schema";

import type { GridColumn, GridTree } from "./columns";
import { rowNature, RowNatureIcon } from "./row-nature";

/** A node of a structure, as the API reads it. */
export type Node = components["schemas"]["Node"];

/** The totals of a reading of the nodes, which the server computes. */
export type NodeTotals = components["schemas"]["NodeTotals"];

/** The answer of `listNodes`: the nodes, depth first, and their totals. */
export type NodeList = operations["listNodes"]["responses"][200]["content"]["application/json"];

/** A column of the contract the server sorts the nodes by. */
export type NodeSortColumn = NonNullable<
  NonNullable<operations["listNodes"]["parameters"]["query"]>["sort_by"]
>;

/** What a grid of a structure asks the server to render: the tasks, the lines. */
export type NodeKind = components["schemas"]["NodeKind"];

/** How the label of a node stands out: a summary in bold, a provision muted. */
function emphasis(node: Node): "strong" | "muted" | undefined {
  const nature = rowNature(node);
  if (nature === "summary") {
    return "strong";
  }
  return nature === "provision" ? "muted" : undefined;
}

/** The tree of a structure: the level the API computes, the icon of the nature of a node. */
export const NODE_TREE: GridTree<Node> = {
  level: (node) => node.level,
  nature: (node) => <RowNatureIcon node={node} />,
  emphasis,
};

/** The identity of a node, stable from one answer to the next. */
export function nodeKey(node: Node): string {
  return node.node_id;
}

/** The number of a node, as the API computes it at the reading. */
export function nodeNumber(node: Node): number {
  return node.row_number;
}

/** The label of a node, pinned at the start: that of the task, or of the line. */
export const LABEL_COLUMN: GridColumn<Node, NodeSortColumn, NodeTotals> = {
  key: "label",
  label: "label",
  format: "text",
  width: 320,
  pinned: true,
  sortBy: "label",
  value: (node) => node.task?.label ?? node.estimate_line?.label,
};
