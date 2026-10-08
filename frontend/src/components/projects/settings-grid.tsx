// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The three dense grids of the settings of a project in the page (FBS-4.2, #301), one component
 * that takes its configuration by its kind: the dense grid, given its configuration here, on the
 * side of the browser — a configuration reads the rows by functions, which never cross from a
 * server component to a client one. The page hands each data only: the rows of the answer, what the
 * address asked, and the settings the session read; the tree of the work breakdown, the project
 * its folds are kept for. Read only: no cell is entered.
 *
 * The totals row says how many the list holds — the order items of the work breakdown, the rows of
 * the answer for the others, the search and the filter applying to it (WF-IHM-0130) —, never a
 * sum.
 */
"use client";

import { useTranslations } from "next-intl";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import {
  BREAKDOWN_GRID,
  type BreakdownRow,
  CONTRIBUTOR_GRID,
  type Contributor,
  SUBPROJECT_GRID,
  type Subproject,
} from "./settings-grids";

/** What a grid of the settings of a project shows, by its kind. */
interface GridProps<Row> {
  readonly rows: readonly Row[];
  readonly query: GridQuery<never>;
  readonly preferences: GridPreferences | undefined;
}

/** The three grids, by their kind: the work breakdown, the sub-projects, the contributors. */
export type SettingsGridProps =
  | ({
      readonly kind: "workBreakdown";
      /** The project whose work breakdown it is: its folds are kept for it. */
      readonly project: string;
      /** How many order items the work breakdown holds. */
      readonly items: number;
    } & GridProps<BreakdownRow>)
  | ({ readonly kind: "subprojects" } & GridProps<Subproject>)
  | ({ readonly kind: "contributors" } & GridProps<Contributor>);

/** Render a grid of the settings of a project, by its kind. */
export function SettingsGrid(props: SettingsGridProps) {
  const t = useTranslations("projectLists");
  switch (props.kind) {
    case "workBreakdown":
      return (
        <DenseGrid
          config={BREAKDOWN_GRID}
          rows={props.rows}
          totals={null}
          totalsCaption={() => t("workBreakdown.count", { count: props.items })}
          query={props.query}
          preferences={props.preferences}
          foldScope={props.project}
        />
      );
    case "subprojects":
      return (
        <DenseGrid
          config={SUBPROJECT_GRID}
          rows={props.rows}
          totals={null}
          totalsCaption={() => t("subprojects.count", { count: props.rows.length })}
          query={props.query}
          preferences={props.preferences}
        />
      );
    case "contributors":
      return (
        <DenseGrid
          config={CONTRIBUTOR_GRID}
          rows={props.rows}
          totals={null}
          totalsCaption={() => t("contributors.count", { count: props.rows.length })}
          query={props.query}
          preferences={props.preferences}
        />
      );
  }
}
