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
 * The totals row says how many the list holds — the elements of the work breakdown the filters
 * retain, by kind, never those shown for the context of what they retain (#574); the rows of the
 * answer for the others —, the search and the filters applying to it (WF-IHM-0130), never a sum. The
 * sub-projects and the contributors sort by the columns of the contract, the server sorting, as the
 * address asks it under the names of their grid. The work breakdown is edited in its grid, as the
 * project lists `update_work_breakdown`, its commands in its bar and in the menu of its cells
 * (`breakdown-commands.tsx`, EP-14/L44c).
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { formatLocale } from "@/i18n/format";

import { useBreakdownCommands, useBreakdownRows } from "./breakdown-commands";
import { useContributorRows } from "./contributor-commands";
import { useBreakdownChips, useContributorChips, useSubprojectChips } from "./settings-chips";

import {
  BREAKDOWN_GRID,
  BREAKDOWN_KINDS,
  type BreakdownKind,
  type BreakdownRow,
  CONTRIBUTOR_GRID,
  type Contributor,
  type ContributorKind,
  type ContributorSort,
  SUBPROJECT_GRID,
  type Subproject,
  subprojectGrid,
  type SubprojectSort,
} from "./settings-grids";
import { useSubprojectRows } from "./subproject-commands";

/**
 * What a grid of the settings of a project shows, by its kind: its rows, its query, its settings.
 */
interface GridProps<Row, Sort extends string> {
  readonly rows: readonly Row[];
  readonly query: GridQuery<Sort>;
  readonly preferences: GridPreferences | undefined;
  /** The filters of the screen, which the bar of the grid folds into its panel (#2916); none, no panel. */
  readonly panel?: ReactNode;
}

/** The three grids, by their kind: the work breakdown, the sub-projects, the contributors. */
export type SettingsGridProps =
  | ({
      readonly kind: "workBreakdown";
      /** The project whose work breakdown it is: its folds are kept for it. */
      readonly project: string;
      /** Whether the reading is filtered: an empty one then says nothing of the work breakdown. */
      readonly filtered?: boolean;
      /** The kinds the address restricts the work breakdown to, told as a chip. */
      readonly kinds?: readonly BreakdownKind[] | undefined;
    } & GridProps<BreakdownRow, never>)
  | ({
      readonly kind: "subprojects";
      /**
       * Whether each row offers its modification and its deletion, as it lists them: the project
       * lists `update`, available or not.
       */
      readonly editable?: boolean;
      /** Whether the address retains the sub-projects charged with actual costs, or the others. */
      readonly actualCosts?: boolean | undefined;
    } & GridProps<Subproject, SubprojectSort>)
  | ({
      readonly kind: "contributors";
      /** The capacities the address restricts the contributors to, and the state of their accounts. */
      readonly kinds?: readonly ContributorKind[] | undefined;
      readonly active?: boolean | undefined;
    } & GridProps<Contributor, ContributorSort>);

/** The grid of the sub-projects, with the columns of the commands of its rows. */
const EDITABLE_SUBPROJECT_GRID = subprojectGrid(true);

/** Render the grid of the sub-projects, each row as the server last answered it. */
function SubprojectGrid({
  rows,
  editable = false,
  query,
  preferences,
  panel,
  actualCosts,
}: Omit<Extract<SettingsGridProps, { kind: "subprojects" }>, "kind">) {
  const t = useTranslations("projectLists");
  const chips = useSubprojectChips(actualCosts);
  const shown = useSubprojectRows(rows);
  return (
    <DenseGrid
      config={editable ? EDITABLE_SUBPROJECT_GRID : SUBPROJECT_GRID}
      rows={shown}
      totals={null}
      totalsCaption={() => t("subprojects.count", { count: shown.length })}
      query={query}
      preferences={preferences}
      filtering={panel === undefined ? undefined : { panel, chips }}
    />
  );
}

/**
 * Render the grid of the work breakdown, as the server last answered it, with its commands; its
 * totals count the elements the filters retain, by kind.
 */
function BreakdownGrid({
  rows,
  project,
  filtered = false,
  query,
  preferences,
  panel,
  kinds,
}: Omit<Extract<SettingsGridProps, { kind: "workBreakdown" }>, "kind">) {
  const t = useTranslations("projectLists.workBreakdown");
  const chips = useBreakdownChips(kinds);
  const locale = useLocale();
  const shown = useBreakdownRows(rows);
  const commands = useBreakdownCommands();
  const retained = BREAKDOWN_KINDS.map((kind) => ({
    kind,
    count: shown.filter((row) => row.matched && row.kind === kind).length,
  }))
    .filter(({ count }) => count > 0)
    .map((counted) => t("retained", counted));
  return (
    <DenseGrid
      config={BREAKDOWN_GRID}
      rows={shown}
      totals={null}
      totalsCaption={() =>
        retained.length === 0
          ? t(shown.length === 0 && !filtered ? "noOrderItem" : "noneRetained")
          : new Intl.ListFormat(formatLocale(locale), { type: "conjunction" }).format(retained)
      }
      query={query}
      preferences={preferences}
      filtering={panel === undefined ? undefined : { panel, chips }}
      foldScope={project}
      commands={commands}
    />
  );
}

/** Render the grid of the contributors, as the server last answered their list. */
function ContributorGrid({
  rows,
  query,
  preferences,
  panel,
  kinds,
  active,
}: Omit<Extract<SettingsGridProps, { kind: "contributors" }>, "kind">) {
  const t = useTranslations("projectLists");
  const chips = useContributorChips(kinds, active);
  const shown = useContributorRows(rows);
  return (
    <DenseGrid
      config={CONTRIBUTOR_GRID}
      rows={shown}
      totals={null}
      totalsCaption={() => t("contributors.count", { count: shown.length })}
      query={query}
      preferences={preferences}
      filtering={panel === undefined ? undefined : { panel, chips }}
    />
  );
}

/** Render a grid of the settings of a project, by its kind. */
export function SettingsGrid(props: SettingsGridProps) {
  switch (props.kind) {
    case "workBreakdown":
      return <BreakdownGrid {...props} />;
    case "subprojects":
      return <SubprojectGrid {...props} />;
    case "contributors":
      return <ContributorGrid {...props} />;
  }
}
