// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The link in conflict a task bears (`link_conflicts`, WF-PLA-0020, WF-IHM-0070), named for the
 * grid of the planning and the Gantt: a manual task a link of its automatic predecessors cannot
 * satisfy, and that predecessor, each naming the link — the row of the predecessor and the type of
 * the link, then the row of the successor when the rows read hold it. The conflict is read from the
 * task, never deduced from its dates (WF-ARC-0020).
 */
"use client";

import { useTranslations } from "next-intl";
import { createContext, useContext } from "react";

import type { components } from "@/api/generated/schema";

/** A link a manual task cannot be satisfied by, or that its predecessor does not satisfy. */
type LinkConflict = components["schemas"]["LinkConflict"];

/** A link of a task to one of its predecessors (WF-PLA-0030). */
type Predecessor = components["schemas"]["Predecessor"];

/** What names a link in conflict of a node: its own row, its predecessors, its conflicts. */
export interface ConflictedNode {
  readonly node_id: string;
  readonly row_number?: number | undefined;
  readonly predecessors?: readonly Predecessor[] | undefined;
  readonly task?: { readonly link_conflicts?: readonly LinkConflict[] | undefined } | null;
}

/**
 * The row number of a task of the rows the grid read, by its node: none for a task a search left
 * out. Given by the grid to the cells that name a link in conflict by its other task.
 */
export const RowNumbers = createContext<(nodeId: string) => number | undefined>(() => undefined);

/**
 * The sentences that name the links in conflict a node bears, one each, in the language: none for a
 * node without one. The row of a task the rows read do not hold is left out of the sentence.
 */
export function useConflictNames(node: ConflictedNode): readonly string[] {
  const t = useTranslations("planningGrid");
  const rowOf = useContext(RowNumbers);
  const rowNumber = (conflict: LinkConflict, side: "predecessor" | "successor") => {
    const id = conflict[`${side}_node_id`];
    return (
      (id === node.node_id ? node.row_number : undefined) ??
      node.predecessors?.find((link) => link.predecessor_node_id === id)?.predecessor_row_number ??
      rowOf(id)
    );
  };
  return (node.task?.link_conflicts ?? []).map((conflict) =>
    t("conflict", {
      predecessor: rowNumber(conflict, "predecessor")?.toString() ?? "",
      code: t("linkCode", { link: conflict.link_type }),
      successor: rowNumber(conflict, "successor")?.toString() ?? "unknown",
    }),
  );
}
