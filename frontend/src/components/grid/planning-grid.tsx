// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the planning in the page: the dense grid — the one component the grid of the
 * estimate renders too —, given its configuration here, on the side of the browser, where the
 * functions of a configuration live. The page hands it data only: the answer of `listNodes`,
 * what the address asked, and the settings the session read. It also lends the cells the row
 * numbers of the answer, by which a predecessor is named.
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";

import { DenseGrid } from "./dense-grid";
import type { NodeList, NodeSortColumn } from "./nodes";
import { PLANNING_GRID } from "./planning";
import { RowNumbers } from "./planning-cells";
import type { GridQuery } from "./query";
import type { GridPreferences } from "./settings";

/** What the grid of the planning shows. */
export interface PlanningGridProps {
  readonly nodes: NodeList;
  readonly query: GridQuery<NodeSortColumn>;
  readonly preferences: GridPreferences | undefined;
}

/** Render the grid of the planning, its totals counting the tasks the answer retained. */
export function PlanningGrid({ nodes, query, preferences }: PlanningGridProps) {
  const t = useTranslations("planningGrid");
  const rows = useMemo(
    () => new Map(nodes.items.map((node) => [node.node_id, node.row_number])),
    [nodes.items],
  );
  return (
    <RowNumbers value={rows}>
      <DenseGrid
        config={PLANNING_GRID}
        rows={nodes.items}
        totals={nodes.totals}
        totalsCaption={t("totals", { tasks: nodes.totals.task_count })}
        query={query}
        preferences={preferences}
      />
    </RowNumbers>
  );
}
