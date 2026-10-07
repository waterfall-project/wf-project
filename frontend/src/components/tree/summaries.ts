// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The task tree of a revision (FBS-4.3.5, WF-PLA-0110): its summary tasks, under a root that stands
 * for the project, down to the depth the user chooses — neither its milestones nor its leaves,
 * which say the work to do, not how the business is broken down. A plan of leaves alone is the
 * root alone.
 *
 * The contract does not say which nodes the tree holds: `listNodes` filters neither on the summary
 * nor on the depth (#463). Until it does, the tree keeps, of the tasks the
 * server renders in the order of the plan, the summaries whose level — as the API computes it — is
 * within the depth asked, and hangs each under its parent, as the API names it: nothing is ordered
 * nor computed here. The depth goes by the address (`depth`), so that a link shared shows the same
 * tree. Pure, and neither server nor client.
 */
import type { SearchParameters } from "@/navigation/context";

/** What the tree reads of a task: its identity, its parent, its number, its level, its label. */
export interface TreeTask {
  readonly node_id: string;
  readonly parent_id: string | null;
  readonly row_number: number;
  readonly level: number;
  readonly task?: { readonly label: string; readonly is_summary: boolean } | null;
}

/** A node of the tree: a summary, by its number and its label, and the summaries under it. */
export interface TreeNode {
  readonly id: string;
  readonly row: number;
  readonly label: string;
  readonly children: readonly TreeNode[];
}

/** The parameter of the address the depth goes by. */
export const DEPTH = "depth";

/** The depth shown when the address asks none: the first two levels. */
const DEFAULT_DEPTH = 2;

/** The deepest level among the summaries, the deepest the tree may show; 0 without any. */
export function deepest(tasks: readonly TreeTask[]): number {
  return tasks.reduce(
    (depth, node) => (node.task?.is_summary === true ? Math.max(depth, node.level) : depth),
    0,
  );
}

/**
 * The depth the address asks, within the levels the tree has; the first two levels, or fewer when
 * there are fewer, when it asks none the tree has.
 */
export function readDepth(search: SearchParameters, levels: number): number {
  const asked = Number.parseInt(search.get(DEPTH) ?? "", 10);
  if (Number.isInteger(asked) && asked >= 1 && asked <= levels) {
    return asked;
  }
  return Math.min(DEFAULT_DEPTH, levels);
}

/**
 * The summaries of the tasks down to a depth, each under its parent, in the order of the answer:
 * those of the first level under the root.
 */
export function summaryTree(tasks: readonly TreeTask[], depth: number): readonly TreeNode[] {
  const children = new Map<string | null, TreeNode[]>();
  const kept = tasks.filter((node) => node.task?.is_summary === true && node.level <= depth);
  const ids = new Set(kept.map((node) => node.node_id));
  for (const node of kept) {
    const parent = node.parent_id !== null && ids.has(node.parent_id) ? node.parent_id : null;
    children.set(parent, [...(children.get(parent) ?? []), placeholder(node)]);
  }
  const grown = (node: TreeNode): TreeNode => ({
    ...node,
    children: (children.get(node.id) ?? []).map(grown),
  });
  return (children.get(null) ?? []).map(grown);
}

/** A node of the tree before its children are hung under it. */
function placeholder(node: TreeTask): TreeNode {
  return { id: node.node_id, row: node.row_number, label: node.task?.label ?? "", children: [] };
}

/** The address of the tree at a depth, the rest of its query kept: the reading context. */
export function depthHref(pathname: string, query: URLSearchParams, depth: number): string {
  const next = new URLSearchParams(query);
  next.set(DEPTH, depth.toString());
  return `${pathname}?${next.toString()}`;
}
