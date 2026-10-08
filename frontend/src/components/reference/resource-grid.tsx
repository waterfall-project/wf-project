// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The three dense grids of the settings of the resources in the page (FBS-3.2, #511), one component
 * that takes its configuration by its kind: the dense grid, given its configuration here, on the side of the browser — a configuration reads the rows
 * by functions, which never cross from a server component to a client one. The page hands each
 * data only: the rows of the answer, what the address asked, the settings the session read, and
 * whether the session may reactivate what it shows deactivated. Read only: no cell is entered.
 *
 * The totals row says how many rows the answer holds — the search and the filter applying to it
 * (WF-IHM-0130) —, never a sum; for the tree, the ancestors the server gives with the nodes a
 * search retains included.
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";

import type { GridConfig } from "@/components/grid/columns";
import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";

import {
  type Calendar,
  type CalendarSort,
  calendarGrid,
  type OrgNode,
  orgNodeGrid,
  type ResourceRole,
  type ResourceRoleSort,
  resourceRoleGrid,
} from "./resource-grids";

/** What a grid of the settings of the resources shows, by its kind. */
interface GridProps<Row, Sort extends string> {
  readonly rows: readonly Row[];
  readonly query: GridQuery<Sort>;
  readonly preferences: GridPreferences | undefined;
  /** Whether the session may modify the settings of the resources (`platformOffer`). */
  readonly reactivable: boolean;
}

/** The three grids, by their kind: the tree of the organisation, the roles, the calendars. */
export type ResourceGridProps =
  | ({ readonly kind: "orgNodes" } & GridProps<OrgNode, never>)
  | ({ readonly kind: "resourceRoles" } & GridProps<ResourceRole, ResourceRoleSort>)
  | ({ readonly kind: "calendars" } & GridProps<Calendar, CalendarSort>);

/** A grid of its configuration, made once for whether the session may reactivate. */
function ReferenceGrid<Row extends object, Sort extends string>({
  make,
  count,
  tree,
  rows,
  query,
  preferences,
  reactivable,
}: GridProps<Row, Sort> & {
  readonly make: (reactivable: boolean) => GridConfig<Row, Sort, null>;
  /** What the totals row says of the rows of the answer. */
  readonly count: (rows: number) => string;
  /** Whether the grid is a tree, which a search unfolds above the rows it retains. */
  readonly tree: boolean;
}) {
  const config = useMemo(() => make(reactivable), [make, reactivable]);
  return (
    <DenseGrid
      config={config}
      rows={rows}
      totals={null}
      totalsCaption={() => count(rows.length)}
      query={query}
      preferences={preferences}
      narrowing={tree ? { search: query.search } : undefined}
    />
  );
}

/** Render a grid of the settings of the resources, by its kind. */
export function ResourceGrid(props: ResourceGridProps) {
  const t = useTranslations("reference");
  switch (props.kind) {
    case "orgNodes":
      return (
        <ReferenceGrid
          {...props}
          make={orgNodeGrid}
          count={(count) => t("orgNodes.count", { count })}
          tree
        />
      );
    case "resourceRoles":
      return (
        <ReferenceGrid
          {...props}
          make={resourceRoleGrid}
          count={(count) => t("resourceRoles.count", { count })}
          tree={false}
        />
      );
    case "calendars":
      return (
        <ReferenceGrid
          {...props}
          make={calendarGrid}
          count={(count) => t("calendars.count", { count })}
          tree={false}
        />
      );
  }
}
