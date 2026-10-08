// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The dense grids of the reference data in their pages (FBS-3.1, FBS-3.2, #510, #511): the tree of
 * the organisation, the roles and the calendars of the settings of the resources, one component
 * that takes its configuration by its kind — the natures and the categories of cost are given theirs
 * the same way (`cost-grid.tsx`). The dense grid is given its configuration here, on the side of the
 * browser: a configuration reads the rows by functions, which never cross from a server component to
 * a client one. The page hands each data only: the rows of the answer, where the page stands in the
 * list for a list the server pages, what the address asked and the settings the session read. Read
 * only: no cell is entered; the reactivation of an object follows the commands it carries.
 *
 * The totals row says how many the list holds — as the server counts those it retained
 * (`meta.total`), the search and the filters applying to it (WF-IHM-0130), never a count of the
 * page; for the tree, read whole, the rows of the answer, the ancestors the server gives with the
 * nodes retained included —, never a sum.
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";

import type { GridConfig } from "@/components/grid/columns";
import { DenseGrid } from "@/components/grid/dense-grid";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import type { ListPage } from "@/navigation/pages";

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

/** What a grid of the reference data shows, by its kind. */
export interface ReferenceGridProps<Row, Sort extends string> {
  readonly rows: readonly Row[];
  readonly query: GridQuery<Sort>;
  readonly preferences: GridPreferences | undefined;
}

/** What a list the server pages adds: where its page stands in it. */
interface Paged {
  readonly page: ListPage;
}

/**
 * What the tree adds: what narrows it — its search and its filters —, which unfolds the ancestors
 * of the rows it retains, once for each narrowing.
 */
interface Narrowed {
  readonly narrowing: Readonly<Record<string, unknown>>;
}

/** The three grids of the settings of the resources, by their kind. */
export type ResourceGridProps =
  | ({ readonly kind: "orgNodes" } & ReferenceGridProps<OrgNode, never> & Narrowed)
  | ({ readonly kind: "resourceRoles" } & ReferenceGridProps<ResourceRole, ResourceRoleSort> &
      Paged)
  | ({ readonly kind: "calendars" } & ReferenceGridProps<Calendar, CalendarSort> & Paged);

/**
 * A grid of its configuration, made once: its totals row the number the server retained for a list
 * it pages, the rows of the answer otherwise.
 */
export function ReferenceGrid<Row extends object, Sort extends string>({
  make,
  count,
  rows,
  query,
  preferences,
  page,
  narrowing,
}: ReferenceGridProps<Row, Sort> & {
  readonly make: () => GridConfig<Row, Sort, null>;
  /** What the totals row says of the number of rows the list holds. */
  readonly count: (rows: number) => string;
  /** Where the page stands in the list the server pages; none for the tree, read whole. */
  readonly page?: ListPage | undefined;
  readonly narrowing?: Readonly<Record<string, unknown>> | undefined;
}) {
  const config = useMemo(() => make(), [make]);
  return (
    <DenseGrid
      config={config}
      rows={rows}
      totals={null}
      totalsCaption={() => count(page === undefined ? rows.length : page.total)}
      query={query}
      preferences={preferences}
      narrowing={narrowing}
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
        />
      );
    case "resourceRoles":
      return (
        <ReferenceGrid
          {...props}
          make={resourceRoleGrid}
          count={(count) => t("resourceRoles.count", { count })}
        />
      );
    case "calendars":
      return (
        <ReferenceGrid
          {...props}
          make={calendarGrid}
          count={(count) => t("calendars.count", { count })}
        />
      );
  }
}
