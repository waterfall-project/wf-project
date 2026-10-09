// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The task tree drawn (FBS-4.3.5, WF-PLA-0110): a `tree` of ARIA, read and never entered (EP-02,
 * « Arborescence de tâches ») — the root for the project, the summaries of the first level side by
 * side under it, each deeper level down under its parent, the layout that holds a tree on a page
 * (WF-PLA-0120). Each summary is named by its number and its label, as the API gives them.
 *
 * It is one stop of the tabulation, its active item, which the arrows move as in any tree: up and
 * down through the items in their order, left to the parent, right to the first child, Home and End
 * to the first and the last. Nothing folds — the depth chosen decides what shows —, and no key
 * changes a task.
 */
"use client";

import { type KeyboardEvent, useRef, useState } from "react";

import { cn } from "@/components/ui/utils";

import type { TreeNode } from "./summaries";

/** An item of the tree, in the order a reader goes through them, with its parent. */
interface Item {
  readonly id: string;
  readonly parent: string | undefined;
  readonly first: string | undefined;
}

/** The items of the tree in the order they show, depth first. */
function itemsOf(nodes: readonly TreeNode[], parent: string | undefined): Item[] {
  return nodes.flatMap((node) => [
    { id: node.id, parent, first: node.children[0]?.id },
    ...itemsOf(node.children, node.id),
  ]);
}

/** The item a key moves to from another, if any. */
function moved(items: readonly Item[], from: string, key: string): string | undefined {
  const at = items.findIndex((item) => item.id === from);
  const item = items[at];
  switch (key) {
    case "ArrowDown":
      return items[at + 1]?.id;
    case "ArrowUp":
      return items[at - 1]?.id;
    case "ArrowLeft":
      return item?.parent;
    case "ArrowRight":
      return item?.first;
    case "Home":
      return items[0]?.id;
    case "End":
      return items.at(-1)?.id;
    default:
      return undefined;
  }
}

/** The classes of the box of an item, the active one ringed when it has the focus. */
const BOX =
  "inline-flex items-baseline gap-1.5 rounded-md border bg-background px-2 py-1 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring";

/** A summary, and those under it, at its level. */
function Branch({
  node,
  level,
  active,
}: {
  readonly node: TreeNode;
  readonly level: number;
  readonly active: string;
}) {
  return (
    <li
      role="treeitem"
      aria-level={level}
      aria-selected={node.id === active}
      aria-expanded={node.children.length === 0 ? undefined : true}
      tabIndex={node.id === active ? 0 : -1}
      data-item={node.id}
      className="outline-none [&:focus-visible>span]:ring-2 [&:focus-visible>span]:ring-ring"
    >
      <span className={BOX}>
        <span className="text-xs text-muted-foreground tabular-nums">{node.row}</span>
        <span>{node.label}</span>
      </span>
      {node.children.length === 0 ? null : (
        <ul role="group" className="mt-1 ml-3 space-y-1 border-l pl-3">
          {node.children.map((child) => (
            <Branch key={child.id} node={child} level={level + 1} active={active} />
          ))}
        </ul>
      )}
    </li>
  );
}

/** Render the task tree of a project, under the root that names it. */
export function TaskTree({
  name,
  project,
  nodes,
}: {
  /** The name of the tree, for a reader of the screen. */
  readonly name: string;
  /** The label of the project, at the root. */
  readonly project: string;
  readonly nodes: readonly TreeNode[];
}) {
  const root = "project";
  const items: Item[] = [
    { id: root, parent: undefined, first: nodes[0]?.id },
    ...itemsOf(nodes, root),
  ];
  const [active, setActive] = useState(root);
  const tree = useRef<HTMLUListElement>(null);
  const shown = items.some((item) => item.id === active) ? active : root;
  const onKeyDown = (event: KeyboardEvent) => {
    const next = moved(items, shown, event.key);
    if (next === undefined) {
      return;
    }
    event.preventDefault();
    setActive(next);
    tree.current?.querySelector<HTMLElement>(`[data-item="${next}"]`)?.focus();
  };
  return (
    <ul ref={tree} role="tree" aria-label={name} onKeyDown={onKeyDown} className="overflow-auto">
      <li
        role="treeitem"
        aria-level={1}
        aria-selected={shown === root}
        aria-expanded={nodes.length === 0 ? undefined : true}
        tabIndex={shown === root ? 0 : -1}
        data-item={root}
        className="flex flex-col items-start gap-3 outline-none [&:focus-visible>span]:ring-2 [&:focus-visible>span]:ring-ring"
      >
        <span className={cn(BOX, "font-semibold")}>{project}</span>
        {nodes.length === 0 ? null : (
          <ul role="group" className="flex flex-wrap items-start gap-4">
            {nodes.map((node) => (
              <Branch key={node.id} node={node} level={2} active={shown} />
            ))}
          </ul>
        )}
      </li>
    </ul>
  );
}
