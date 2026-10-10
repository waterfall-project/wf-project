// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the resources (FBS-3.2, US-0250), outside any project: the organisation
 * (FBS-3.2.1), the resource roles (FBS-3.2.2), the calendars (FBS-3.2.3) — three dense grids, each
 * searched and filtered by the server and, for the roles and the calendars, bounded on their figures,
 * sorted and paged by it, as the address asks under the names of each grid (#301, #511, #533, #545)
 * — and the constants the units
 * of duration convert by, under the same permission as the calendars (WF-PLA-0160). Each object
 * names those it is attached to as the server resolves them. Every figure as the API gives it: the
 * front sorts, filters and pages nothing.
 *
 * The lists hold the active objects alone, and the deactivated ones too when the address asks for
 * them and the session may read them (WF-REF-0150, `include_inactive`); each object carries the
 * command that reactivates it, as the server lists it. The roles are filtered by a node of the
 * organisation chosen among the whole tree — read whole a second time when a search or a filter
 * narrows the grid of the tree —, by a category of cost and by a calendar chosen among every one the
 * session reads, each read whole as a list of choices is (#303); the categories, which the
 * settings of the costs keep, are offered only when the API gives them. A session that may modify the
 * settings of the resources creates and modifies the nodes, the roles and the calendars, and
 * deactivates them as each lists it (EP-02/L43b): a role is attached to a category of labour alone
 * (WF-REF-0090), which each category says (`cost_type_kind`, EP-14/L43g); the screen then says that
 * the fake back keeps none of what is written (`MockupNotice`). Bounds the API refuses (422,
 * an upper bound below the lower one) leave their list unread, the bound said at its field; any other
 * read the API refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import type { ApiClient } from "@/api/client";
import { readEveryPage, readEveryPageUnlessRefused } from "@/api/every-page";
import { type ExpectedRefusal, readOrFail, type ReadOrRefused, readOrRefused } from "@/api/problem";
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
  asksInactive,
  given,
  identifierOf,
  inactiveQuery,
  type KeptGrids,
  levelOf,
  shownPage,
  stateOf,
  textOf,
} from "@/components/reference/address";
import { categoryChoice, labourOf } from "@/components/reference/kinds";
import { InactiveSwitch } from "@/components/reference/reference-filters";
import {
  CALENDAR_ADDRESS,
  CALENDAR_GRID_KEY,
  CALENDAR_SORTS,
  CALENDAR_STATE,
  type CalendarSort,
  calendarDay,
  DAYS,
  type Day,
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
  ROLE_COST_CATEGORY,
  ROLE_HEADCOUNT,
  ROLE_MONTHLY_HOURS,
  ROLE_ORG_NODE,
  ROLE_STATE,
  type ResourceRoleSort,
} from "@/components/reference/resource-grids";
import {
  CalendarList,
  type DayBounds,
  DurationUnitFacts,
  type NodeOffered,
  type OrgNodeFilters,
  OrgNodeList,
  ResourceRoleList,
  type RoleFilters,
} from "@/components/reference/resource-lists";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { MockupNotice } from "@/components/shell/mockup-notice";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch, type SearchParameters } from "@/navigation/context";
import { offsetOf } from "@/navigation/pages";
import { type Permission, requestSession } from "@/session/request";

import { screenMetadata } from "../../title";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.resourceSettings");
}

/** The pages of the lists the server pages, which the switch of the deactivated objects resets. */
const PAGES = [RESOURCE_ROLE_ADDRESS.offset, CALENDAR_ADDRESS.offset] as const;

/** The refusals a list of choices is done without on: not found, or refused. */
const REFUSED = [{ status: 404 }, { status: 403 }] as const;

/** The refusal of the bounds of a list: an upper bound below the lower one (#545). */
const BOUNDS_REFUSED = [{ status: 422, code: "VALIDATION_FAILED" }] as const;

/**
 * The title of the screen, and the switch of the deactivated objects for who may read them; under it,
 * for who may write, that the fake back keeps nothing of what is written.
 */
function ResourcesHeader({
  inactive,
  writes,
}: {
  readonly inactive: boolean | undefined;
  /** Whether the session may modify the settings of the resources, and its commands write. */
  readonly writes: boolean;
}) {
  const t = useTranslations("functions");
  return (
    <>
      <PageHeader
        title={t("resourceSettings")}
        icon={FUNCTION_ICONS.resource_settings}
        density={FUNCTION_DENSITY.resource_settings}
        actions={
          inactive === undefined ? undefined : <InactiveSwitch shown={inactive} pages={PAGES} />
        }
      />
      {writes ? <MockupNotice /> : null}
    </>
  );
}

/** The bounds of a column of the address, under the names of the contract for that column. */
function bounds<Column extends string>(column: Column, { min, max }: Bounds) {
  return { ...given(`${column}_min`, min), ...given(`${column}_max`, max) } as Partial<
    Record<`${Column}_min` | `${Column}_max`, string>
  >;
}

/** The bounds of the hours of each day, under the names of the contract. */
function dayBounds(hours: DayBounds) {
  return Object.fromEntries(
    DAYS.flatMap((day) => Object.entries(bounds(day, hours[day]))),
  ) as Partial<Record<`${Day}_min` | `${Day}_max`, string>>;
}

/** What the page asks of each list, as its address and the session say. */
interface ResourceQueries {
  /** Whether the session may modify the settings of the resources, and its forms are offered. */
  readonly editable: boolean;
  readonly inactive: { readonly include_inactive?: true };
  /** What the categories of cost offered to the filter of the roles ask of the deactivated ones. */
  readonly inactiveCategories: { readonly include_inactive?: true };
  readonly nodes: GridQuery<never>;
  readonly nodeFilters: OrgNodeFilters;
  readonly roles: GridQuery<ResourceRoleSort>;
  readonly roleFilters: RoleFilters;
  readonly roleOffset: number | undefined;
  readonly calendars: GridQuery<CalendarSort>;
  readonly calendarState: boolean | undefined;
  readonly calendarHours: DayBounds;
  readonly calendarOffset: number | undefined;
}

/** The tree of the organisation as the address narrows it; none when nothing narrows it. */
function readNarrowedTree(client: ApiClient, { inactive, nodes, nodeFilters }: ResourceQueries) {
  const { code, level, state, levels } = nodeFilters;
  if (
    nodes.search === undefined &&
    code === undefined &&
    level === undefined &&
    state === undefined &&
    !bounded(levels)
  ) {
    return undefined;
  }
  return readOrRefused("listOrgNodes", BOUNDS_REFUSED, () =>
    client.GET("/reference/org-nodes", {
      params: {
        query: {
          ...inactive,
          ...searched(nodes),
          ...given("code", code),
          ...given("level", level),
          ...given("level_min", levels.min === undefined ? undefined : Number(levels.min)),
          ...given("level_max", levels.max === undefined ? undefined : Number(levels.max)),
          ...given("is_active", state),
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
  { inactive, roles, roleFilters, roleOffset }: ResourceQueries,
) {
  return readOrRefused("listResourceRoles", BOUNDS_REFUSED, () =>
    client.GET("/reference/resource-roles", {
      params: {
        query: {
          ...inactive,
          ...asked(roles, roleOffset),
          ...given("org_node_id", roleFilters.orgNode),
          ...given("cost_category_id", roleFilters.category),
          ...given("calendar_id", roleFilters.calendar),
          ...given("is_active", roleFilters.state),
          ...bounds("monthly_hours", roleFilters.monthlyHours),
          ...bounds("headcount", roleFilters.headcount),
        },
      },
    }),
  );
}

/** The page of the calendars the address asks, filtered, bounded and sorted as it says. */
function readCalendars(
  client: ApiClient,
  { inactive, calendars, calendarState, calendarHours, calendarOffset }: ResourceQueries,
) {
  return readOrRefused("listCalendars", BOUNDS_REFUSED, () =>
    client.GET("/reference/calendars", {
      params: {
        query: {
          ...inactive,
          ...asked(calendars, calendarOffset),
          ...given("is_active", calendarState),
          ...dayBounds(calendarHours),
        },
      },
    }),
  );
}

/**
 * The categories of cost and the calendars the roles may be filtered on, every one the session
 * reads, as a list of choices is read (#303): the categories none when the API refuses them. Each
 * category says the type of its nature, by which a role is attached to a category of labour alone
 * (WF-REF-0090, `cost_type_kind`).
 */
function readChoices(client: ApiClient, { inactive, inactiveCategories }: ResourceQueries) {
  return Promise.all([
    readEveryPageUnlessRefused("listCostCategories", REFUSED, (page) =>
      client.GET("/reference/cost-categories", {
        params: { query: { ...inactiveCategories, ...page } },
      }),
    ),
    readEveryPage("listCalendars", (page) =>
      client.GET("/reference/calendars", { params: { query: { ...inactive, ...page } } }),
    ),
  ]);
}

/** Read the lists of the settings of the resources, as the address asks them. */
async function readLists(queries: ResourceQueries) {
  const client = serverClient();
  return Promise.all([
    readNarrowedTree(client, queries),
    readOrFail("listOrgNodes", () =>
      client.GET("/reference/org-nodes", { params: { query: { ...queries.inactive } } }),
    ),
    readRoles(client, queries),
    readCalendars(client, queries),
    readOrFail("getDurationUnits", () => client.GET("/reference/duration-units")),
    readChoices(client, queries),
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
  const state = (name: string) => stateOf(search, name, permissions, "resource_settings.read");
  return {
    editable: platformOffer(permissions, "resource_settings") !== undefined,
    inactive: inactiveQuery(asksInactive(search), permissions, "resource_settings.read"),
    inactiveCategories: inactiveQuery(asksInactive(search), permissions, "cost_settings.read"),
    nodes: readGridQuery<never>(search, [], undefined, ORG_NODE_ADDRESS),
    nodeFilters: {
      code: textOf(search, ORG_CODE, ORG_CODE_LENGTH),
      level: levelOf(search, ORG_LEVEL),
      state: state(ORG_STATE),
      levels: readBounds(search, ORG_LEVEL, "level"),
    },
    roles: readGridQuery(
      search,
      RESOURCE_ROLE_SORTS,
      grids?.[RESOURCE_ROLE_GRID_KEY]?.sort,
      RESOURCE_ROLE_ADDRESS,
    ),
    roleFilters: {
      orgNode: identifierOf(search, ROLE_ORG_NODE),
      category: identifierOf(search, ROLE_COST_CATEGORY),
      calendar: identifierOf(search, ROLE_CALENDAR),
      state: state(ROLE_STATE),
      monthlyHours: readBounds(search, ROLE_MONTHLY_HOURS, "decimal"),
      headcount: readBounds(search, ROLE_HEADCOUNT, "decimal"),
    },
    roleOffset: offsetOf(search.get(RESOURCE_ROLE_ADDRESS.offset)),
    calendars: readGridQuery(
      search,
      CALENDAR_SORTS,
      grids?.[CALENDAR_GRID_KEY]?.sort,
      CALENDAR_ADDRESS,
    ),
    calendarState: state(CALENDAR_STATE),
    calendarHours: Object.fromEntries(
      DAYS.map((day) => [day, readBounds(search, calendarDay(day), "decimal")]),
    ) as DayBounds,
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
  const grids = session?.user.display_preferences?.grids ?? undefined;
  const queries = readQueries(search, grids, permissions);
  const [narrowed, tree, roles, calendars, units, [categoryRead, calendarRead]] =
    await readLists(queries);
  const { editable } = queries;
  const readsInactive = permissions.includes("resource_settings.read");
  const shown = queries.inactive.include_inactive === true;
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
        <ResourcesHeader inactive={readsInactive ? shown : undefined} writes={editable} />
        <OrgNodeList
          {...narrowedTree(narrowed, tree)}
          query={queries.nodes}
          preferences={keptBy(grids, ORG_NODE_GRID_KEY)}
          readsInactive={readsInactive}
          editable={editable}
          filters={queries.nodeFilters}
          levels={Array.from({ length: deepest }, (_, at) => at + 1)}
          nodes={nodes}
        />
        <ResourceRoleList
          {...shownPage(roles)}
          query={queries.roles}
          preferences={keptBy(grids, RESOURCE_ROLE_GRID_KEY)}
          readsInactive={readsInactive}
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
          {...shownPage(calendars)}
          query={queries.calendars}
          preferences={keptBy(grids, CALENDAR_GRID_KEY)}
          readsInactive={readsInactive}
          editable={editable}
          state={queries.calendarState}
          hours={queries.calendarHours}
        />
        <DurationUnitFacts units={units} />
      </PendingAddress>
    </Screen>
  );
}
