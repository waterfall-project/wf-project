// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the comparison of two revisions (US-0500, FBS-4.1): the dense grid of the structures,
 * read only, on the nodes `compareRevisions` renders — the tree of the revision compared, each
 * node with the mark of its difference from the revision of base, the nodes removed at the place
 * they had. A column of marks heads it (`GridConfig.difference`), `+`, `-` and `M` doubled by the
 * colour of the row, as the grid of a differential bears them; then the number of the node, its
 * label indented by its level and marked by the icon of its kind, and what changes of it
 * (`changes`), named as the server names it. The front pairs nothing, sums nothing and orders
 * nothing (WF-ARC-0020): the order is the plan's, no header sorts, nothing is searched, and the
 * totals are those of the answer. The page hands it data only; its functions live on the side of
 * the browser, its configuration in `comparison-columns.tsx`, which the help reads too.
 */
"use client";

import { useTranslations } from "next-intl";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { NodeSortColumn, NodeTotals } from "@/components/grid/nodes";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import { COMPARISON_GRID } from "./comparison-columns";
import type { ComparisonRow } from "./comparison-rows";

/** What the grid asks of the address: nothing, it sorts and searches nothing. */
const UNASKED: GridQuery<NodeSortColumn> = { sort: undefined, search: undefined, size: undefined };

/** What the grid of the comparison shows. */
export interface ComparisonGridProps {
  /** The nodes of the comparison, in the order of the plan, as the grid reads them. */
  readonly rows: readonly ComparisonRow[];
  /** The totals of the revision compared, as the server computes them. */
  readonly totals: NodeTotals;
  /** The settings of the grid the session read, if any. */
  readonly preferences: GridPreferences | undefined;
}

/** Render the grid of the comparison of two revisions. */
export function ComparisonGrid({ rows, totals, preferences }: ComparisonGridProps) {
  const t = useTranslations("estimateGrid");
  return (
    <DenseGrid
      config={COMPARISON_GRID}
      rows={rows}
      totals={totals}
      totalsCaption={(counted) =>
        t("totals", { tasks: counted.task_count, lines: counted.estimate_line_count })
      }
      query={UNASKED}
      preferences={preferences}
    />
  );
}
