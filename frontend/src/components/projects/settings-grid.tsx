// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The three dense grids of the settings of a project in the page (FBS-4.2, #301), one component
 * that takes its configuration by its kind: the dense grid, given its configuration here, on the
 * side of the browser — a configuration reads the rows by functions, which never cross from a
 * server component to a client one. The page hands each data only: the rows of the answer, what the
 * address asked, and the settings the session read; the tree of the work breakdown, the project
 * its folds are kept for. No cell is entered: the sub-projects, offered to a session the project
 * lists `update` to, each have their modification and their deletion in columns of their own
 * (`subproject-commands.tsx`), and a row answered or deleted shows as the server answered it, as do
 * the contributors once their list is written (`contributor-commands.tsx`).
 *
 * The totals row says how many the list holds — the order items of the work breakdown, the rows of
 * the answer for the others, the search and the filters applying to it (WF-IHM-0130) —, never a
 * sum. The sub-projects and the contributors sort by the columns of the contract, the server
 * sorting, as the address asks it under the names of their grid.
 */
"use client";

import { useTranslations } from "next-intl";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import { useContributorRows } from "./contributor-commands";

import {
  BREAKDOWN_GRID,
  type BreakdownRow,
  CONTRIBUTOR_GRID,
  type Contributor,
  type ContributorSort,
  SUBPROJECT_GRID,
  type Subproject,
  type SubprojectSort,
} from "./settings-grids";
import { DeleteSubproject, ModifySubproject, useSubprojectRows } from "./subproject-commands";

/**
 * What a grid of the settings of a project shows, by its kind: its rows, its query, its settings.
 */
interface GridProps<Row, Sort extends string> {
  readonly rows: readonly Row[];
  readonly query: GridQuery<Sort>;
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
    } & GridProps<BreakdownRow, never>)
  | ({
      readonly kind: "subprojects";
      /**
       * Whether each row offers its modification and its deletion, as it lists them: the project
       * lists `update`, available or not.
       */
      readonly editable?: boolean;
    } & GridProps<Subproject, SubprojectSort>)
  | ({ readonly kind: "contributors" } & GridProps<Contributor, ContributorSort>);

/** The grid of the sub-projects, with the columns of the commands of its rows. */
const EDITABLE_SUBPROJECT_GRID: typeof SUBPROJECT_GRID = {
  ...SUBPROJECT_GRID,
  columns: [
    ...SUBPROJECT_GRID.columns,
    {
      key: "modify",
      label: "modify",
      format: "text",
      width: 110,
      value: () => null,
      render: (row) => <ModifySubproject row={row} />,
    },
    {
      key: "delete",
      label: "delete",
      format: "text",
      width: 120,
      value: () => null,
      render: (row) => <DeleteSubproject row={row} />,
    },
  ],
};

/** Render the grid of the sub-projects, each row as the server last answered it. */
function SubprojectGrid({
  rows,
  editable = false,
  query,
  preferences,
}: Omit<Extract<SettingsGridProps, { kind: "subprojects" }>, "kind">) {
  const t = useTranslations("projectLists");
  const shown = useSubprojectRows(rows);
  return (
    <DenseGrid
      config={editable ? EDITABLE_SUBPROJECT_GRID : SUBPROJECT_GRID}
      rows={shown}
      totals={null}
      totalsCaption={() => t("subprojects.count", { count: shown.length })}
      query={query}
      preferences={preferences}
    />
  );
}

/** Render the grid of the contributors, as the server last answered their list. */
function ContributorGrid({
  rows,
  query,
  preferences,
}: Omit<Extract<SettingsGridProps, { kind: "contributors" }>, "kind">) {
  const t = useTranslations("projectLists");
  const shown = useContributorRows(rows);
  return (
    <DenseGrid
      config={CONTRIBUTOR_GRID}
      rows={shown}
      totals={null}
      totalsCaption={() => t("contributors.count", { count: shown.length })}
      query={query}
      preferences={preferences}
    />
  );
}

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
      return <SubprojectGrid {...props} />;
    case "contributors":
      return <ContributorGrid {...props} />;
  }
}
