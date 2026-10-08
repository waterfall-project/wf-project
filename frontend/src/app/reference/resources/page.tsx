// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the resources (FBS-3.2, US-0250), outside any project: the organisation
 * (FBS-3.2.1), the resource roles (FBS-3.2.2), the calendars (FBS-3.2.3) — three dense grids, each
 * searched by the server and, for the roles and the calendars, sorted by it, as the address asks
 * under the names of each grid (#301, #511) — and the constants the units of duration convert by,
 * under the same permission as the calendars (WF-PLA-0160). Each object names those it is
 * attached to as the server resolves them. Every figure as the API gives it: the front sorts and
 * filters nothing.
 *
 * The lists hold the active objects alone, and the deactivated ones too when the address asks for
 * them and the session may read them (WF-REF-0150, `include_inactive`); a session that may modify
 * the settings of the resources reactivates them. The roles are restricted to a node of the
 * organisation the address names, chosen among the whole tree — read whole a second time when a
 * search narrows the grid of the tree. A read the API refuses, or cannot answer, is thrown for the
 * pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { platformOffer } from "@/components/commands/offer";
import { PendingAddress } from "@/components/grid/pending-address";
import { type GridQuery, readGridQuery } from "@/components/grid/query";
import { asksInactive, identifierOf, inactiveQuery } from "@/components/reference/address";
import { InactiveSwitch } from "@/components/reference/reference-filters";
import {
  CALENDAR_ADDRESS,
  CALENDAR_GRID_KEY,
  CALENDAR_SORTS,
  type CalendarSort,
  ORG_NODE_ADDRESS,
  ORG_NODE_GRID_KEY,
  RESOURCE_ROLE_ADDRESS,
  RESOURCE_ROLE_GRID_KEY,
  RESOURCE_ROLE_SORTS,
  ROLE_ORG_NODE,
  type ResourceRoleSort,
} from "@/components/reference/resource-grids";
import {
  CalendarList,
  DurationUnitFacts,
  OrgNodeList,
  ResourceRoleList,
} from "@/components/reference/resource-lists";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch, type SearchParameters } from "@/navigation/context";
import { type Permission, requestSession, type Session } from "@/session/request";

import { screenMetadata } from "../../title";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.resourceSettings");
}

/** The title of the screen, and the switch of the deactivated objects for who may read them. */
function ResourcesHeader({ inactive }: { readonly inactive: boolean | undefined }) {
  const t = useTranslations("functions");
  return (
    <PageHeader
      title={t("resourceSettings")}
      icon={FUNCTION_ICONS.resource_settings}
      density={FUNCTION_DENSITY.resource_settings}
      actions={inactive === undefined ? undefined : <InactiveSwitch shown={inactive} />}
    />
  );
}

/** A search of the address, by the name of the contract: none when the address holds none. */
function searched<Sort extends string>(query: GridQuery<Sort>) {
  return query.search === undefined ? {} : { search: query.search };
}

/** A sort of the address, by the names of the contract: none when the address asks none. */
function sorted<Sort extends string>(query: GridQuery<Sort>) {
  return query.sort === undefined
    ? {}
    : { sort_by: query.sort.column, sort_order: query.sort.order };
}

/** What the page asks of each list, as its address and the session say. */
interface ResourceQueries {
  readonly inactive: { readonly include_inactive?: true };
  readonly nodes: GridQuery<never>;
  readonly roles: GridQuery<ResourceRoleSort>;
  readonly calendars: GridQuery<CalendarSort>;
  readonly orgNode: string | undefined;
}

/** Read the lists of the settings of the resources, as the address asks them. */
async function readLists({ inactive, nodes, roles, calendars, orgNode }: ResourceQueries) {
  const client = serverClient();
  return Promise.all([
    nodes.search === undefined
      ? undefined
      : readOrFail("listOrgNodes", () =>
          client.GET("/reference/org-nodes", {
            params: { query: { ...inactive, ...searched(nodes) } },
          }),
        ),
    readOrFail("listOrgNodes", () =>
      client.GET("/reference/org-nodes", { params: { query: { ...inactive } } }),
    ),
    readOrFail("listResourceRoles", () =>
      client.GET("/reference/resource-roles", {
        params: {
          query: {
            ...inactive,
            ...searched(roles),
            ...sorted(roles),
            ...(orgNode === undefined ? {} : { org_node_id: orgNode }),
          },
        },
      }),
    ),
    readOrFail("listCalendars", () =>
      client.GET("/reference/calendars", {
        params: { query: { ...inactive, ...searched(calendars), ...sorted(calendars) } },
      }),
    ),
    readOrFail("getDurationUnits", () => client.GET("/reference/duration-units")),
  ]);
}

/** The settings of the grids the account keeps. */
type GridSettings = NonNullable<
  NonNullable<NonNullable<Session["user"]["display_preferences"]>["grids"]>
>;

/** What the page asks of each list, from its address, the sort each grid keeps and the session. */
function readQueries(
  search: SearchParameters,
  grids: GridSettings | undefined,
  permissions: readonly Permission[],
): ResourceQueries {
  return {
    inactive: inactiveQuery(asksInactive(search), permissions, "resource_settings.read"),
    nodes: readGridQuery<never>(search, [], undefined, ORG_NODE_ADDRESS),
    roles: readGridQuery(
      search,
      RESOURCE_ROLE_SORTS,
      grids?.[RESOURCE_ROLE_GRID_KEY]?.sort,
      RESOURCE_ROLE_ADDRESS,
    ),
    calendars: readGridQuery(
      search,
      CALENDAR_SORTS,
      grids?.[CALENDAR_GRID_KEY]?.sort,
      CALENDAR_ADDRESS,
    ),
    orgNode: identifierOf(search, ROLE_ORG_NODE),
  };
}

/** Render the settings of the resources. */
export default async function ResourceSettingsPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const [search, session] = await Promise.all([
    searchParams.then((asked) => pageSearch(asked)),
    requestSession(),
  ]);
  const permissions = session?.permissions ?? [];
  const grids = session?.user.display_preferences?.grids ?? undefined;
  const queries = readQueries(search, grids, permissions);
  const [narrowed, tree, roles, calendars, units] = await readLists(queries);
  const reactivable = platformOffer(permissions, "resource_settings") !== undefined;
  const shown = queries.inactive.include_inactive === true;
  return (
    <Screen density={FUNCTION_DENSITY.resource_settings}>
      <PendingAddress>
        <ResourcesHeader
          inactive={permissions.includes("resource_settings.read") ? shown : undefined}
        />
        <OrgNodeList
          rows={narrowed ?? tree}
          query={queries.nodes}
          preferences={grids?.[ORG_NODE_GRID_KEY] ?? undefined}
          reactivable={reactivable}
        />
        <ResourceRoleList
          rows={roles}
          query={queries.roles}
          preferences={grids?.[RESOURCE_ROLE_GRID_KEY] ?? undefined}
          reactivable={reactivable}
          nodes={tree.map((node) => ({
            id: node.org_node_id,
            code: node.code,
            label: node.label,
            level: node.level,
          }))}
          orgNode={queries.orgNode}
        />
        <CalendarList
          rows={calendars}
          query={queries.calendars}
          preferences={grids?.[CALENDAR_GRID_KEY] ?? undefined}
          reactivable={reactivable}
        />
        <DurationUnitFacts units={units} />
      </PendingAddress>
    </Screen>
  );
}
