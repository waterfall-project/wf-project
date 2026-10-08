// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configurations of the three dense grids of the settings of the resources (FBS-3.2, #301,
 * #511): the tree of the organisation, the resource roles, the calendars. Three grids on one
 * screen, each with the key of its settings in the account (WF-ADM-0040) and its own names in the
 * address (`prefixedAddress`), under which its page asks the API by the names of the contract.
 *
 * - The organisation is a tree (WF-REF-0070, no limit of depth): it sorts by no column
 *   (`sorts: false`) — the order is the tree's, as `listOrgNodes` gives it —, folds and unfolds as the grids of the tasks do
 *   (`GridTree.parent`, `fold.tsx`), and is searched by the server, which gives the nodes retained
 *   with their ancestors (WF-PLA-0080).
 * - The roles are a flat table: each column the contract sorts by sorts (WF-IHM-0060), searched
 *   by the server, filtered by node (`org_node_id`).
 * - The calendars are a flat table: the label, the default one and the state sort; the hours of a
 *   day do not, the contract sorting by those of the whole week alone, which no column shows.
 *
 * The contract filters the roles by their label and their node alone, the calendars and the tree
 * by their label alone, and sorts no hours of a day: the filters of the other columns, and that
 * sort, are #533.
 *
 * Neither server nor client: the page reads the keys, the names and the columns sorted; the grids,
 * in the browser, the rest — the functions that read a row never cross to the server.
 */
import { CalendarCheck } from "lucide-react";
import { useTranslations } from "next-intl";

import type { components, operations } from "@/api/generated/schema";
import { type GridColumn, type GridConfig, sortColumns } from "@/components/grid/columns";
import { prefixedAddress } from "@/components/grid/query";
import { ICON } from "@/components/projects/project-tables";

import { StateCell } from "./reactivation";

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

/** The node the roles are restricted to, in the address: `org_node_id` of the contract. */
export const ROLE_ORG_NODE = "role_org_node_id";

/** The seven days of a calendar, from Monday, as the contract names them. */
const DAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const satisfies readonly (keyof Calendar["weekly_hours"])[];

/** The width of the column of the state, its command of reactivation beside the mark. */
const STATE_WIDTH = 190;

/** The column of the state of an object, and the command that reactivates it where allowed. */
function stateColumn<Row, Sort extends string>(
  read: (row: Row) => {
    readonly active: boolean;
    readonly target: Parameters<typeof StateCell>[0]["target"];
    readonly name: string;
  },
  reactivable: boolean,
  contract: Sort | undefined,
): GridColumn<Row, Sort, null> {
  return {
    key: "state",
    label: "state",
    format: "text",
    width: STATE_WIDTH,
    ...(contract === undefined ? {} : { contract }),
    value: (row) => (read(row).active ? "active" : "inactive"),
    render: (row) => {
      const { active, target, name } = read(row);
      return <StateCell active={active} target={target} name={name} reactivable={reactivable} />;
    },
  };
}

/**
 * The tree of the organisation: each node by its label, set in by its depth under its parent and
 * folding the nodes under it, its code, its depth and its state.
 */
export function orgNodeGrid(reactivable: boolean): GridConfig<OrgNode, never, null> {
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
      stateColumn<OrgNode, never>(
        (node) => ({
          active: node.is_active,
          target: { kind: "org_node", id: node.org_node_id, lockVersion: node.lock_version },
          name: node.label,
        }),
        reactivable,
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
  reactivable: boolean,
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
      stateColumn<ResourceRole, ResourceRoleSort>(
        (role) => ({
          active: role.is_active,
          target: {
            kind: "resource_role",
            id: role.resource_role_id,
            lockVersion: role.lock_version,
          },
          name: role.label,
        }),
        reactivable,
        "is_active",
      ),
    ],
  };
}

/** The mark of the default calendar: an icon and its words. */
function DefaultCalendar({ calendar }: { readonly calendar: Calendar }) {
  const t = useTranslations("reference.calendars");
  return calendar.is_default ? (
    <span className="inline-flex items-center gap-1.5">
      <CalendarCheck aria-hidden="true" className={ICON} />
      {t("isDefault")}
    </span>
  ) : null;
}

/**
 * The calendars: each by its seven values of hours from Monday, the default one marked
 * (WF-REF-0110, WF-REF-0120), and its state.
 */
export function calendarGrid(reactivable: boolean): GridConfig<Calendar, CalendarSort, null> {
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
        value: (calendar) => calendar.weekly_hours[day],
      })),
      {
        key: "is_default",
        label: "defaultCalendar",
        format: "text",
        width: 180,
        contract: "is_default",
        value: (calendar) => (calendar.is_default ? "default" : null),
        render: (calendar) => <DefaultCalendar calendar={calendar} />,
      },
      stateColumn<Calendar, CalendarSort>(
        (calendar) => ({
          active: calendar.is_active,
          target: {
            kind: "calendar",
            id: calendar.calendar_id,
            lockVersion: calendar.lock_version,
          },
          name: calendar.label,
        }),
        reactivable,
        "is_active",
      ),
    ],
  };
}

/** The columns of the contract the server sorts the roles and the calendars by. */
export const RESOURCE_ROLE_SORTS = sortColumns(resourceRoleGrid(false));
export const CALENDAR_SORTS = sortColumns(calendarGrid(false));
