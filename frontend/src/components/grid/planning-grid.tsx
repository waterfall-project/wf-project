// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the planning in the page: the dense grid — the one component the grid of the
 * estimate renders too —, given its configuration here, on the side of the browser, where the
 * functions of a configuration live. The page hands it data only: the rows of the answer of
 * `listNodes` as the grid reads them (`projectNodes`), the structure they belong to, what the
 * address asked, and the settings the session read. A computed cell asks the server what its
 * value depends on, by the structure and its node. The Gantt, its last column, lays out the rows
 * the grid shows once for all its cells (`GanttRows`).
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";

import { GanttRows } from "@/components/gantt/gantt";

import { DenseGrid } from "./dense-grid";
import { nodeDependencies } from "./node-dependencies";
import type { NodeRows, NodeSortColumn, StructurePath } from "./nodes";
import { PLANNING_GRID, type PlanningNode } from "./planning";
import type { GridQuery } from "./query";
import type { GridPreferences } from "./settings";

/** What the grid of the planning shows. */
export interface PlanningGridProps {
  /** The rows of the answer of `listNodes`, as the grid reads them, and its totals. */
  readonly nodes: NodeRows<PlanningNode>;
  /** The structure the rows belong to. */
  readonly structure: StructurePath;
  readonly query: GridQuery<NodeSortColumn>;
  readonly preferences: GridPreferences | undefined;
  /**
   * Whether the revision may be planned (`edit_planning`): its grid places undo and redo, which
   * act on the entries of the planning once EP-06 keeps them; none, and it places none.
   */
  readonly undoable?: boolean | undefined;
}

/** Render the grid of the planning, its totals counting the tasks the answer retained. */
export function PlanningGrid({
  nodes,
  structure,
  query,
  preferences,
  undoable,
}: PlanningGridProps) {
  const t = useTranslations("planningGrid");
  // A reader for each reading: an answer names rows a new reading may have renumbered.
  const dependencies = useMemo(
    () => nodeDependencies(structure, nodes.items),
    [structure, nodes.items],
  );
  return (
    <DenseGrid
      config={PLANNING_GRID}
      rows={nodes.items}
      totals={nodes.totals}
      totalsCaption={(totals) => t("totals", { tasks: totals.task_count })}
      query={query}
      preferences={preferences}
      dependencies={dependencies}
      undoable={undoable}
      around={(rows, table) => <GanttRows rows={rows}>{table}</GanttRows>}
    />
  );
}
