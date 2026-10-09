// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the remaining to commit in the page: the dense grid — the one component the grids of
 * the planning and of the estimate render too —, given its configuration here, on the side of the
 * browser, where the functions of a configuration live. The page hands it data only: the rows of
 * the answer of `listNodes` as the grid reads them (`projectNodes`), the structure they belong to,
 * what the reading asked of the nodes, whether the remaining to commit may be entered, what the
 * address asked, and the settings the session read. A computed cell asks the server what its value
 * depends on, by the structure and its node; a figure entered is written by the structure and its
 * node too (`setLineRemaining`). What a write answers is read as the grid reads it
 * (`nodesWritten`), but its totals: the reading narrows to the tasks started — the not started
 * too, when asked —, and reads its own totals anew once its writes answered (`readNodeTotals`). Its
 * tree folds as the planning's, the folds kept for the revision.
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";

import { readNodeTotals, setLineRemaining } from "@/api/actions/nodes";

import { DenseGrid } from "./dense-grid";
import { nodeDependencies } from "./node-dependencies";
import {
  type NodeFilters,
  nodeNarrowing,
  type NodeRows,
  type NodeSortColumn,
  nodesWritten,
  type StructurePath,
} from "./nodes";
import type { GridQuery } from "./query";
import {
  REMAINING_FIELDS,
  remainingGrid,
  type RemainingNode,
  type RemainingWrites,
} from "./remaining";
import type { GridPreferences } from "./settings";

/**
 * What the reading asks that is the scope of the grid, not a filter: the states of the tasks — the
 * started ones, the not started on demand (WF-RAE-0040) —, which unfolds nothing.
 */
const SCOPE = ["progress"] as const;

/** What the grid of the remaining to commit shows. */
export interface RemainingGridProps {
  /** The rows of the answer of `listNodes`, as the grid reads them, and its totals. */
  readonly nodes: NodeRows<RemainingNode>;
  /** The structure the rows belong to. */
  readonly structure: StructurePath;
  /**
   * What the reading asked of the nodes besides their fields and their sort, as it was sent — the
   * states of the tasks always —, whose totals the grid reads anew by the same request.
   */
  readonly filters: NodeFilters;
  /**
   * Whether the remaining to commit may be entered: the revision lists `edit_remaining` available
   * to the caller. Then the grid places undo and redo too (US-0140); otherwise it is read only.
   */
  readonly editable: boolean;
  readonly query: GridQuery<NodeSortColumn>;
  readonly preferences: GridPreferences | undefined;
}

/**
 * How the grid re-estimates a line: the figure entered and the version of the node read
 * (`lock_version`), nothing else — the answer read as the grid reads it. The reading always
 * narrows to some states of the tasks (`progress`): its totals are never those of the structure a
 * write answers, and are read anew by the same request.
 */
function structureWrites(structure: StructurePath, filters: NodeFilters): RemainingWrites {
  return {
    totals: () => readNodeTotals(structure, filters),
    line: async (node, basis) => {
      const outcome = await setLineRemaining(structure, node.node_id, {
        reestimated_amount_basis: basis,
        lock_version: node.lock_version,
      });
      return outcome.kind === "done"
        ? { kind: "done", data: nodesWritten(outcome.data, REMAINING_FIELDS, false) }
        : outcome;
    },
  };
}

/** Render the grid of the remaining to commit, its totals counting the tasks and lines retained. */
export function RemainingGrid({
  nodes,
  structure,
  filters,
  editable,
  query,
  preferences,
}: RemainingGridProps) {
  const t = useTranslations("estimateGrid");
  // A reader for each reading: an answer names rows a new reading may have renumbered.
  const dependencies = useMemo(
    () => nodeDependencies(structure, nodes.items),
    [structure, nodes.items],
  );
  const config = useMemo(
    () => remainingGrid(editable ? structureWrites(structure, filters) : undefined),
    [editable, structure, filters],
  );
  return (
    <DenseGrid
      config={config}
      rows={nodes.items}
      totals={nodes.totals}
      totalsCaption={(totals) =>
        t("totals", { tasks: totals.task_count, lines: totals.estimate_line_count })
      }
      query={query}
      preferences={preferences}
      dependencies={dependencies}
      foldScope={structure.revision_id}
      narrowing={nodeNarrowing(filters, SCOPE)}
      undoable={editable}
    />
  );
}
