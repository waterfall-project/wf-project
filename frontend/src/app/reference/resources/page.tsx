// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the resources (FBS-3.2, US-0250), outside any project: the organisation
 * (FBS-3.2.1), the resource roles (FBS-3.2.2), the calendars (FBS-3.2.3) — three dense grids, each
 * searched and filtered by the server and, for the roles, bounded on their figures, sorted and
 * paged by it, as the address asks under the names of each grid (#301, #511, #533, #545); the
 * calendars bound no hours of a day (WF-IHM-0130-A) — and the constants the units of duration
 * convert by, under the same permission as the calendars (WF-PLA-0160). Each object names those it
 * is attached to as the server resolves them. Every figure as the API gives it: the front sorts,
 * filters and pages nothing.
 *
 * Each list shows the state its own filter says (WF-REF-0150, US-2090): the active objects alone by
 * default, said by the chip « Actifs (par défaut) », the deactivated ones alone, or every one, the
 * chip lifted — the address says it under the name of each grid, else the account kept it with the
 * settings of the grid (`stateOf`); the screen has no switch of its own, and `include_inactive` in
 * its address is no longer read (#3076). Only a session that may modify the settings
 * (`resource_settings.write`) is offered the filter, without which the contract refuses the
 * deactivated objects (403): another reads the active ones alone. Each object carries the command
 * that reactivates it, as the server lists it. The roles are filtered by their code, by a node of the
 * organisation chosen among the active tree — read whole, and a second time when a search or a filter
 * narrows the grid of the tree, its state included unless it is the default —, by a category of cost
 * and by a calendar chosen among the active ones the session reads, each read whole as a list of
 * choices is (#303), and which the forms offer, whatever the lists show; the categories, which the
 * settings of the costs keep, are offered only when
 * the API gives them. A session that may modify the settings of the resources creates and modifies
 * the nodes, the roles and the calendars, and deactivates them as each lists it (EP-02/L43b): a
 * role is attached to a category of labour alone (WF-REF-0090), which each category says
 * (`cost_type_kind`, EP-14/L43g). The service keeps what is written and filters what is asked: the
 * screen shows no mock-up notice (US-0850). Bounds the API refuses (422, an upper bound below the
 * lower one) leave their list unread, the bound said at its field; any other read the API
 * refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import type { ApiClient } from "@/api/client";
import { readEveryPage, readEveryPageUnlessRefused } from "@/api/every-page";
import {
  type ExpectedRefusal,
  OPTIONAL_READ_REFUSALS,
  readOrFail,
  type ReadOrRefused,
  readOrRefused,
} from "@/api/problem";
import { serverClient } from "@/api/server";
import { platformOffer } from "@/components/commands/offer";
import {
  type Bounds,
  bounded,
  readBounds,
  type RefusedBounds,
  refusedBounds,
} from "@/components/grid/filters";
import { PendingAddress } from "@/components/grid/pending-address";
import { asked, type GridQuery, readGridQuery, searched } from "@/components/grid/query";
import {
  given,
  identifierOf,
  type KeptGrids,
  levelOf,
  shownPage,
  stateOf,
  stateQuery,
  textOf,
} from "@/components/reference/address";
import { categoryChoice, labourOf } from "@/components/reference/kinds";
import {
  CALENDAR_ADDRESS,
  CALENDAR_GRID_KEY,
  CALENDAR_SORTS,
  CALENDAR_STATE,
  type CalendarSort,
  ORG_CODE,
  ORG_CODE_LENGTH,
  ORG_LEVEL,
  ORG_NODE_ADDRESS,
  ORG_NODE_GRID_KEY,
  ORG_STATE,
  RESOURCE_ROLE_ADDRESS,
  RESOURCE_ROLE_GRID_KEY,
  RESOURCE_ROLE_SORTS,
  ROLE_CALENDAR,
  ROLE_CODE,
  ROLE_COST_CATEGORY,
  ROLE_HEADCOUNT,
  ROLE_MONTHLY_HOURS,
  ROLE_ORG_NODE,
  ROLE_STATE,
  type ResourceRoleSort,
} from "@/components/reference/resource-grids";
import {
  CalendarList,
  DurationUnitFacts,
  type NodeOffered,
  type OrgNodeFilters,
  OrgNodeList,
  ResourceRoleList,
  type RoleFilters,
} from "@/components/reference/resource-lists";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch, type SearchParameters } from "@/navigation/context";
import { offsetOf } from "@/navigation/pages";
import { type Permission, requestSession } from "@/session/request";

import { screenMetadata } from "../../title";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.resourceSettings");
}

/** The refusal of the bounds of a list: an upper bound below the lower one (#545). */
const BOUNDS_REFUSED = [{ status: 422, code: "VALIDATION_FAILED" }] as const;

/** The title of the screen. */
function ResourcesHeader() {
  const t = useTranslations("functions");
  return (
    <PageHeader
      title={t("resourceSettings")}
      icon={FUNCTION_ICONS.resource_settings}
      density={FUNCTION_DENSITY.resource_settings}
    />
  );
}

/** The bounds of a column of the address, under the names of the contract for that column. */
function bounds<Column extends string>(column: Column, { min, max }: Bounds) {
  return { ...given(`${column}_min`, min), ...given(`${column}_max`, max) } as Partial<
    Record<`${Column}_min` | `${Column}_max`, string>
  >;
}

/** What the page asks of each list, as its address and the session say. */
interface ResourceQueries {
  /** Whether the session may modify the settings of the resources, and its forms are offered. */
  readonly editable: boolean;
  readonly nodes: GridQuery<never>;
  readonly nodeFilters: OrgNodeFilters;
  readonly roles: GridQuery<ResourceRoleSort>;
  readonly roleFilters: RoleFilters;
  readonly roleOffset: number | undefined;
  readonly calendars: GridQuery<CalendarSort>;
  readonly calendarState: boolean | undefined;
  readonly calendarOffset: number | undefined;
}

/**
 * The tree of the organisation as the address narrows it; none when nothing narrows it — the active
 * nodes, the state by default or the one a session that may not read the deactivated ones reads,
 * being the whole tree read.
 */
function readNarrowedTree(client: ApiClient, { editable, nodes, nodeFilters }: ResourceQueries) {
  const { code, level, state, levels } = nodeFilters;
  if (
    nodes.search === undefined &&
    code === undefined &&
    level === undefined &&
    (state === true || !editable) &&
    !bounded(levels)
  ) {
    return undefined;
  }
  return readOrRefused("listOrgNodes", BOUNDS_REFUSED, () =>
    client.GET("/reference/org-nodes", {
      params: {
        query: {
          ...searched(nodes),
          ...given("code", code),
          ...given("level", level),
          ...given("level_min", levels.min === undefined ? undefined : Number(levels.min)),
          ...given("level_max", levels.max === undefined ? undefined : Number(levels.max)),
          ...stateQuery(state, editable),
        },
      },
    }),
  );
}

/**
 * What the tree shows: the nodes the address narrows it to, the whole tree when nothing narrows it,
 * or no node and the bounds the API refused.
 */
function narrowedTree<Node>(
  narrowed: ReadOrRefused<Node[], ExpectedRefusal> | undefined,
  tree: Node[],
): { readonly rows: readonly Node[]; readonly refused: RefusedBounds | undefined } {
  if (narrowed === undefined) {
    return { rows: tree, refused: undefined };
  }
  return narrowed.kind === "read"
    ? { rows: narrowed.data, refused: undefined }
    : { rows: [], refused: refusedBounds(narrowed.problem.fields ?? []) };
}

/** The page of the roles the address asks, filtered, bounded and sorted as it says. */
function readRoles(
  client: ApiClient,
  { editable, roles, roleFilters, roleOffset }: ResourceQueries,
) {
  return readOrRefused("listResourceRoles", BOUNDS_REFUSED, () =>
    client.GET("/reference/resource-roles", {
      params: {
        query: {
          ...asked(roles, roleOffset),
          ...given("code", roleFilters.code),
          ...given("org_node_id", roleFilters.orgNode),
          ...given("cost_category_id", roleFilters.category),
          ...given("calendar_id", roleFilters.calendar),
          ...stateQuery(roleFilters.state, editable),
          ...bounds("monthly_hours", roleFilters.monthlyHours),
          ...bounds("headcount", roleFilters.headcount),
        },
      },
    }),
  );
}

/**
 * The page of the calendars the address asks, searched, filtered and sorted as it says: the
 * contract bounds no hours of a day (C-352, #1047, WF-IHM-0130-A).
 */
function readCalendars(
  client: ApiClient,
  { editable, calendars, calendarState, calendarOffset }: ResourceQueries,
) {
  return readOrFail("listCalendars", () =>
    client.GET("/reference/calendars", {
      params: {
        query: {
          ...asked(calendars, calendarOffset),
          ...stateQuery(calendarState, editable),
        },
      },
    }),
  );
}

/**
 * The categories of cost and the calendars the roles may be filtered on, every active one the
 * session reads, as a list of choices is read (#303): the categories none when the API refuses them.
 * Each category says the type of its nature, by which a role is attached to a category of labour
 * alone (WF-REF-0090, `cost_type_kind`).
 */
function readChoices(client: ApiClient) {
  return Promise.all([
    readEveryPageUnlessRefused("listCostCategories", OPTIONAL_READ_REFUSALS, (page) =>
      client.GET("/reference/cost-categories", { params: { query: page } }),
    ),
    readEveryPage("listCalendars", (page) =>
      client.GET("/reference/calendars", { params: { query: page } }),
    ),
  ]);
}

/** Read the lists of the settings of the resources, as the address asks them. */
async function readLists(queries: ResourceQueries) {
  const client = serverClient();
  return Promise.all([
    readNarrowedTree(client, queries),
    readOrFail("listOrgNodes", () => client.GET("/reference/org-nodes")),
    readRoles(client, queries),
    readCalendars(client, queries),
    readOrFail("getDurationUnits", () => client.GET("/reference/duration-units")),
    readChoices(client),
  ]);
}

/** The settings a grid keeps in the account, by its key; none when it keeps none. */
function keptBy(grids: KeptGrids | undefined, key: string) {
  return grids?.[key] ?? undefined;
}

/** What the page asks of each list, from its address, the sort each grid keeps and the session. */
function readQueries(
  search: SearchParameters,
  grids: KeptGrids | undefined,
  permissions: readonly Permission[],
): ResourceQueries {
  // The state each list shows: the address's, else the one its grid keeps, else the active alone.
  const state = (name: string, key: string) =>
    stateOf(
      search,
      name,
      keptBy(grids, key)?.filters?.[name],
      permissions,
      "resource_settings.write",
    );
  return {
    editable: platformOffer(permissions, "resource_settings") !== undefined,
    nodes: readGridQuery<never>(search, [], undefined, ORG_NODE_ADDRESS),
    nodeFilters: {
      code: textOf(search, ORG_CODE, ORG_CODE_LENGTH),
      level: levelOf(search, ORG_LEVEL),
      state: state(ORG_STATE, ORG_NODE_GRID_KEY),
      levels: readBounds(search, ORG_LEVEL, "level"),
    },
    roles: readGridQuery(
      search,
      RESOURCE_ROLE_SORTS,
      grids?.[RESOURCE_ROLE_GRID_KEY]?.sort,
      RESOURCE_ROLE_ADDRESS,
      grids?.[RESOURCE_ROLE_GRID_KEY]?.page_size,
    ),
    roleFilters: {
      code: textOf(search, ROLE_CODE, ORG_CODE_LENGTH),
      orgNode: identifierOf(search, ROLE_ORG_NODE),
      category: identifierOf(search, ROLE_COST_CATEGORY),
      calendar: identifierOf(search, ROLE_CALENDAR),
      state: state(ROLE_STATE, RESOURCE_ROLE_GRID_KEY),
      monthlyHours: readBounds(search, ROLE_MONTHLY_HOURS, "decimal"),
      headcount: readBounds(search, ROLE_HEADCOUNT, "decimal"),
    },
    roleOffset: offsetOf(search.get(RESOURCE_ROLE_ADDRESS.offset)),
    calendars: readGridQuery(
      search,
      CALENDAR_SORTS,
      grids?.[CALENDAR_GRID_KEY]?.sort,
      CALENDAR_ADDRESS,
      grids?.[CALENDAR_GRID_KEY]?.page_size,
    ),
    calendarState: state(CALENDAR_STATE, CALENDAR_GRID_KEY),
    calendarOffset: offsetOf(search.get(CALENDAR_ADDRESS.offset)),
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
  const grids = session?.display_preferences?.grids ?? undefined;
  const queries = readQueries(search, grids, permissions);
  const [narrowed, tree, roles, calendars, units, [categoryRead, calendarRead]] =
    await readLists(queries);
  const { editable } = queries;
  // The depths of the whole tree, from the first to the deepest the server gives.
  const deepest = Math.max(0, ...tree.map((node) => node.level));
  const nodes: NodeOffered[] = tree.map((node) => ({
    id: node.org_node_id,
    code: node.code,
    label: node.label,
    level: node.level,
    active: node.is_active,
  }));
  return (
    <Screen density={FUNCTION_DENSITY.resource_settings}>
      <PendingAddress>
        <ResourcesHeader />
        <OrgNodeList
          {...narrowedTree(narrowed, tree)}
          query={queries.nodes}
          preferences={keptBy(grids, ORG_NODE_GRID_KEY)}
          editable={editable}
          filters={queries.nodeFilters}
          levels={Array.from({ length: deepest }, (_, at) => at + 1)}
          nodes={nodes}
        />
        <ResourceRoleList
          {...shownPage(roles)}
          query={queries.roles}
          preferences={keptBy(grids, RESOURCE_ROLE_GRID_KEY)}
          editable={editable}
          nodes={nodes}
          categories={categoryRead?.map(categoryChoice)}
          labour={labourOf(categoryRead)}
          calendars={calendarRead.map((calendar) => ({
            id: calendar.calendar_id,
            label: calendar.label,
            active: calendar.is_active,
          }))}
          filters={queries.roleFilters}
        />
        <CalendarList
          rows={calendars.items}
          page={calendars.meta}
          query={queries.calendars}
          preferences={keptBy(grids, CALENDAR_GRID_KEY)}
          editable={editable}
          state={queries.calendarState}
        />
        <DurationUnitFacts units={units} editable={editable} />
      </PendingAddress>
    </Screen>
  );
}
