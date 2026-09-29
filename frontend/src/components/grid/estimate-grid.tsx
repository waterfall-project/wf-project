// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the estimate in the page: the dense grid — the one component the grid of the
 * planning renders too —, given its configuration here, on the side of the browser — a
 * configuration reads the rows by functions, which never cross from a server component to a
 * client one. The page hands it data only: the rows of the answer of `listNodes` as the grid
 * reads them (`projectNodes`), what the address asked, and the settings the session read.
 */
"use client";

import { useTranslations } from "next-intl";

import { DenseGrid } from "./dense-grid";
import { ESTIMATE_GRID, type EstimateNode } from "./estimate";
import type { NodeRows, NodeSortColumn } from "./nodes";
import type { GridQuery } from "./query";
import type { GridPreferences } from "./settings";

/** What the grid of the estimate shows. */
export interface EstimateGridProps {
  /** The rows of the answer of `listNodes`, as the grid reads them, and its totals. */
  readonly nodes: NodeRows<EstimateNode>;
  readonly query: GridQuery<NodeSortColumn>;
  readonly preferences: GridPreferences | undefined;
}

/** Render the grid of the estimate, its totals counting the tasks and the lines retained. */
export function EstimateGrid({ nodes, query, preferences }: EstimateGridProps) {
  const t = useTranslations("estimateGrid");
  return (
    <DenseGrid
      config={ESTIMATE_GRID}
      rows={nodes.items}
      totals={nodes.totals}
      totalsCaption={t("totals", {
        tasks: nodes.totals.task_count,
        lines: nodes.totals.estimate_line_count,
      })}
      query={query}
      preferences={preferences}
    />
  );
}
