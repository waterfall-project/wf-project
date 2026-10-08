// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The task tree of a revision (FBS-4.3.5, WF-PLA-0110): its summary tasks, under a root that stands
 * for the project, down to the depth the user chooses — neither its milestones nor its leaves,
 * which say the work to do, not how the business is broken down. A plan of leaves alone is the
 * root alone.
 *
 * The server selects the nodes of the tree (`listNodes`, #463): the summaries alone
 * (`summaries_only`), down to the depth asked (`max_level`), in the order of the plan. The tree
 * applies the same criterion to the answer once more (`summaryTree`) — a temporary gap of EP-02:
 * the fake back ignores the filters of `listNodes`, and the mock-up must stay right against it;
 * against a server that applies them, it changes nothing. It goes with the back of EP-03. The tree
 * hangs each summary under its parent, as the API names it, and orders and computes nothing. The
 * depth goes by the address (`depth`), so that a link shared shows the same tree.
 *
 * The contract does not say how deep the summaries go: the depths offered are those of the
 * summaries of the answer, and the next one when one is at the depth asked, which may have
 * summaries under it — a summary that has none shows the same tree one level deeper. Pure, and
 * neither server nor client.
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

/** The depth asked when the address asks none: the first two levels. */
const DEFAULT_DEPTH = 2;

/** The depth the address asks — a level, the first being 1 —; the first two when it asks none. */
export function readDepth(search: SearchParameters): number {
  const asked = search.get(DEPTH) ?? "";
  const level = /^\d+$/.test(asked) ? Number.parseInt(asked, 10) : Number.NaN;
  return Number.isSafeInteger(level) && level >= 1 ? level : DEFAULT_DEPTH;
}

/**
 * The summaries of the answer down to a depth: what a server that applies `summaries_only` and
 * `max_level` renders, kept once more against one that does not (the fake back of EP-02).
 */
function retained(tasks: readonly TreeTask[], depth: number): readonly TreeTask[] {
  return tasks.filter((node) => node.task?.is_summary === true && node.level <= depth);
}

/**
 * The depths the tree offers, read at a depth: down to the deepest summary of the answer, and one
 * more when that summary is at the depth asked; none for a plan without a summary. An answer that
 * holds deeper summaries than asked — the fake back's — offers them.
 */
export function depthsOffered(tasks: readonly TreeTask[], depth: number): number {
  const deepest = tasks.reduce(
    (level, node) => (node.task?.is_summary === true ? Math.max(level, node.level) : level),
    0,
  );
  return deepest === depth ? deepest + 1 : deepest;
}

/**
 * The depth the tree shows, read at a depth: the one asked, or the deepest of the answer when the
 * answer holds no summary that deep — the tree is then whole.
 */
export function depthShown(tasks: readonly TreeTask[], depth: number): number {
  return Math.min(depth, depthsOffered(tasks, depth));
}

/**
 * The summaries of the answer down to a depth, each under its parent, in the order of the answer:
 * those of the first level, or whose parent the tree does not hold, under the root.
 */
export function summaryTree(tasks: readonly TreeTask[], depth: number): readonly TreeNode[] {
  const kept = retained(tasks, depth);
  const children = new Map<string | null, TreeNode[]>();
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
