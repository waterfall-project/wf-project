// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configurations of the three dense grids of the settings of the resources (FBS-3.2, #301,
 * #511): the tree of the organisation, the resource roles, the calendars. Three grids on one
 * screen, each with the key of its settings in the account (WF-ADM-0040) and its own names in the
 * address (`prefixedAddress`), under which its page asks the API by the names of the contract.
 *
 * - The organisation is a tree (WF-REF-0070, no limit of depth): it sorts by no column
 *   (`sorts: false`) — the order is the tree's, as `listOrgNodes` gives it —, is read whole, never
 *   by pages, folds and unfolds as the grids of the tasks do (`GridTree.parent`, `fold.tsx`), and is
 *   searched and filtered by the server — its code, its depth, its state —, which gives the nodes
 *   retained with their ancestors (WF-PLA-0080).
 * - The roles are a flat table: each column sorts (WF-IHM-0060), searched by the server, filtered
 *   by node, category, calendar and state, and paged by it.
 * - The calendars are a flat table: each column sorts, the hours of each day too, filtered by state
 *   and paged by the server.
 *
 * The columns of figures — the monthly hours and the headcount of a role, the hours of each day of
 * a calendar — are bounded, the least and the most retained, under `<column>_min` and
 * `<column>_max` after the prefix of the grid, as the contract names them for every list (#545,
 * `RangeFilter`).
 *
 * For a session that may modify the settings of the resources, each row offers its modification in a
 * column of its own, and a calendar active and not by default its designation (EP-02/L43b); the state
 * of each object carries the command that changes it as the server lists it (`commandColumns`).
 *
 * Neither server nor client: the page reads the keys, the names and the columns sorted; the grids,
 * in the browser, the rest — the functions that read a row never cross to the server.
 */
import type { components, operations } from "@/api/generated/schema";
import { type GridColumn, type GridConfig, sortColumns } from "@/components/grid/columns";
import { prefixedAddress } from "@/components/grid/query";

import { commandColumns } from "./command-columns";
import { DefaultCalendarCell } from "./calendar-default";

/** A node of the organisation, as the contract gives it. */
export type OrgNode = components["schemas"]["OrgNode"];

/** A resource role, as the contract gives it. */
export type ResourceRole = components["schemas"]["ResourceRole"];

/** A calendar, as the contract gives it. */
export type Calendar = components["schemas"]["Calendar"];

/** The column of the contract the server sorts the roles by. */
export type ResourceRoleSort = NonNullable<
  NonNullable<operations["listResourceRoles"]["parameters"]["query"]>["sort_by"]
>;

/** The column of the contract the server sorts the calendars by. */
export type CalendarSort = NonNullable<
  NonNullable<operations["listCalendars"]["parameters"]["query"]>["sort_by"]
>;

/** The keys of the settings of the three grids in the account: stable. */
export const ORG_NODE_GRID_KEY = "org_nodes";
export const RESOURCE_ROLE_GRID_KEY = "resource_roles";
export const CALENDAR_GRID_KEY = "calendars";

/** The names of each grid in the address: those of the contract, after its prefix. */
export const ORG_NODE_ADDRESS = prefixedAddress("org_");
export const RESOURCE_ROLE_ADDRESS = prefixedAddress("role_");
export const CALENDAR_ADDRESS = prefixedAddress("calendar_");

/**
 * The filters of each grid in the address: those of the contract, after the prefix of its grid —
 * the node, the category, the calendar and the state of the roles, the state of the calendars, the
 * code, the depth and the state of the nodes.
 */
export const ROLE_ORG_NODE = "role_org_node_id";
export const ROLE_COST_CATEGORY = "role_cost_category_id";
export const ROLE_CALENDAR = "role_calendar_id";
export const ROLE_STATE = "role_is_active";
export const CALENDAR_STATE = "calendar_is_active";
export const ORG_CODE = "org_code";
export const ORG_LEVEL = "org_level";
export const ORG_STATE = "org_is_active";

/**
 * The columns of figures each grid bounds, as the address names them after its prefix: their bounds
 * are `<column>_min` and `<column>_max` (`boundNames`).
 */
export const ROLE_MONTHLY_HOURS = "role_monthly_hours";
export const ROLE_HEADCOUNT = "role_headcount";

/** The column of the hours of a day of the calendars, as the address names it after its prefix. */
export function calendarDay(day: Day): string {
  return `calendar_${day}`;
}

/** The longest code of a node the contract filters on (`code` of `listOrgNodes`). */
export const ORG_CODE_LENGTH = 20;

/** The seven days of a calendar, from Monday, as the contract names them. */
export const DAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const satisfies readonly (keyof Calendar["weekly_hours"])[];

/** A day of a calendar, as the contract names it. */
export type Day = (typeof DAYS)[number];

/**
 * The tree of the organisation: each node by its label, set in by its depth under its parent and
 * folding the nodes under it, its code, its depth and its state.
 */
export function orgNodeGrid(editable = false): GridConfig<OrgNode, never, null> {
  return {
    key: ORG_NODE_GRID_KEY,
    name: "orgNodes",
    address: ORG_NODE_ADDRESS,
    sorts: false,
    searched: true,
    rowKey: (node) => node.org_node_id,
    tree: {
      level: (node) => node.level,
      nature: () => null,
      parent: (node) => node.parent_id,
    },
    columns: [
      {
        key: "label",
        label: "label",
        format: "text",
        width: 280,
        pinned: true,
        value: (node) => node.label,
      },
      { key: "code", label: "code", format: "text", width: 110, value: (node) => node.code },
      {
        key: "level",
        label: "level",
        format: "decimal",
        width: 70,
        value: (node) => node.level.toString(),
      },
      ...commandColumns<OrgNode, never>(
        editable,
        (node) => ({
          active: node.is_active,
          target: { kind: "org_node", id: node.org_node_id, lockVersion: node.lock_version },
          name: node.label,
          commands: node.available_commands,
          // The parent to reactivate first (WF-REF-0080), named as the node names it.
          conflict:
            node.parent_id === null || node.parent_label === null
              ? undefined
              : { id: node.parent_id, name: node.parent_label },
        }),
        undefined,
      ),
    ],
  };
}

/**
 * The resource roles: each with its node, its category and its calendar — named as the server
 * resolves them, active or not (WF-REF-0150) —, its capacity in hours a month and the headcount it
 * stands for (WF-REF-0090, WF-REF-0100), and its state; each column sorted by the server.
 */
export function resourceRoleGrid(
  editable = false,
): GridConfig<ResourceRole, ResourceRoleSort, null> {
  return {
    key: RESOURCE_ROLE_GRID_KEY,
    name: "resourceRoles",
    address: RESOURCE_ROLE_ADDRESS,
    searched: true,
    rowKey: (role) => role.resource_role_id,
    columns: [
      {
        key: "label",
        label: "label",
        format: "text",
        width: 220,
        pinned: true,
        contract: "label",
        value: (role) => role.label,
      },
      {
        key: "org_node",
        label: "orgNode",
        format: "text",
        width: 200,
        contract: "org_node",
        value: (role) => role.org_node_label,
      },
      {
        key: "cost_category",
        label: "costCategory",
        format: "text",
        width: 180,
        contract: "cost_category",
        value: (role) => role.cost_category_label,
      },
      {
        key: "calendar",
        label: "calendar",
        format: "text",
        width: 200,
        contract: "calendar",
        value: (role) => role.calendar_label,
      },
      {
        key: "monthly_hours",
        label: "monthlyHours",
        format: "decimal",
        width: 120,
        contract: "monthly_hours",
        value: (role) => role.capacity.monthly_hours,
      },
      {
        key: "headcount",
        label: "headcount",
        format: "decimal",
        width: 90,
        contract: "headcount",
        value: (role) => role.capacity.headcount,
      },
      ...commandColumns<ResourceRole, ResourceRoleSort>(
        editable,
        (role) => ({
          active: role.is_active,
          target: {
            kind: "resource_role",
            id: role.resource_role_id,
            lockVersion: role.lock_version,
          },
          name: role.label,
          commands: role.available_commands,
          // The node to reactivate first (WF-REF-0080), named as the role names it.
          conflict: { id: role.org_node_id, name: role.org_node_label },
        }),
        "is_active",
      ),
    ],
  };
}

/**
 * The calendars: each by its seven values of hours from Monday, the default one marked
 * (WF-REF-0110, WF-REF-0120), and its state; each column sorted by the server.
 */
export function calendarGrid(editable = false): GridConfig<Calendar, CalendarSort, null> {
  return {
    key: CALENDAR_GRID_KEY,
    name: "calendars",
    address: CALENDAR_ADDRESS,
    searched: true,
    rowKey: (calendar) => calendar.calendar_id,
    columns: [
      {
        key: "label",
        label: "label",
        format: "text",
        width: 220,
        pinned: true,
        contract: "label",
        value: (calendar) => calendar.label,
      },
      ...DAYS.map((day): GridColumn<Calendar, CalendarSort, null> => ({
        key: day,
        label: day,
        format: "decimal",
        width: 60,
        contract: day,
        value: (calendar) => calendar.weekly_hours[day],
      })),
      {
        key: "is_default",
        label: "defaultCalendar",
        format: "text",
        width: 180,
        contract: "is_default",
        value: (calendar) => (calendar.is_default ? "default" : null),
        render: (calendar) => <DefaultCalendarCell calendar={calendar} />,
      },
      ...commandColumns<Calendar, CalendarSort>(
        editable,
        (calendar) => ({
          active: calendar.is_active,
          target: {
            kind: "calendar",
            id: calendar.calendar_id,
            lockVersion: calendar.lock_version,
          },
          name: calendar.label,
          commands: calendar.available_commands,
        }),
        "is_active",
      ),
    ],
  };
}

/** The columns of the contract the server sorts the roles and the calendars by. */
export const RESOURCE_ROLE_SORTS = sortColumns(resourceRoleGrid());
export const CALENDAR_SORTS = sortColumns(calendarGrid());
