// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a gesture of a user of the load asks of the API (US-2300, `load.ts`): the readings of the
 * screens of the journey of the grids on PRJ-001 — the grid of the planning, of the estimate and of
 * the remaining to commit, the estimate filtered by a lot, sorted, searched, and the workload of
 * the project —, and the two entries of the planning, a label and a duration that redates its task.
 * Pure, for k6 and for Vitest alike (`screens.test.ts`).
 *
 * A reading asks what carries the screen: for a grid, the structures of the revision and the nodes
 * of the main structure, with the kinds, the fields and the default filters the page of the screen
 * asks (`readGridScreen`); for the workload, the workload, the nodes of organisation and the
 * revisions marked. The requests the server of Next makes beside them for every screen — the
 * session, the project, the navigation — are not replayed: they are small, and the browser of the
 * measure makes them. The fields are written here, k6 not knowing the modules of the front;
 * `screens.test.ts` holds them to those the pages ask (`nodeFieldNames`), so that they do not drift.
 */

/** Where the load reads and writes: the project, its revision, its main structure, a lot. */
export interface Place {
  readonly project: string;
  readonly revision: string;
  readonly structure: string;
  /** A lot of the project, which the estimate is filtered by. */
  readonly workPackage: string;
}

/** A request of a reading: its name, for the summary of k6, and its path and query. */
export interface Asked {
  readonly name: string;
  readonly path: string;
}

/** A reading of a screen: its name, and the requests it makes. */
export interface Reading {
  readonly name: string;
  readonly asks: (place: Place) => readonly Asked[];
}

/** The fields every grid reads (`COMMON_FIELDS` of `src/components/grid/nodes.tsx`). */
const COMMON = {
  node: [
    "node_id",
    "lock_version",
    "computed_fields",
    "editable_fields",
    "row_number",
    "level",
    "parent_id",
    "position",
    "kind",
    "difference",
  ],
  task: ["label", "is_summary", "is_milestone"],
  line: ["label", "is_computed", "resource_role_id"],
} as const;

/** The fields of a grid beyond the common ones, by part of the node. */
interface Fields {
  readonly node: readonly string[];
  readonly task: readonly string[];
  readonly line: readonly string[];
}

/** The names of the fields a grid asks, as the page writes them (`nodeFieldNames`). */
export function fieldNames(fields: Fields): string[] {
  return [
    ...new Set([
      ...COMMON.node,
      ...fields.node,
      ...[...COMMON.task, ...fields.task].map((field) => `task.${field}`),
      ...[...COMMON.line, ...fields.line].map((field) => `estimate_line.${field}`),
    ]),
  ];
}

/** The fields of the planning (`PLANNING_FIELDS`). */
export const PLANNING: Fields = {
  node: ["predecessors", "origin_risk_id"],
  task: [
    "description",
    "scheduling_mode",
    "duration",
    "start",
    "finish",
    "progress",
    "physical_progress",
    "total_float",
    "is_critical",
    "link_conflicts",
    "started_on",
    "completed_on",
    "order_item_id",
    "work_package_id",
    "work_breakdown_label",
    "tracking",
    "calendar_hours",
  ],
  line: [],
};

/** The fields of the estimate (`ESTIMATE_FIELDS`). */
export const ESTIMATE: Fields = {
  node: ["origin_risk_id"],
  task: ["progress", "base_amount", "reestimated_amount"],
  line: [
    "cost_category_id",
    "cost_category_label",
    "resource_role_label",
    "quantity",
    "hours",
    "unit_disbursement",
    "subproject_id",
    "subproject_label",
    "payment_delay_days",
    "uses_inactive_object",
    "base_amount",
    "reestimated_amount",
  ],
};

/** The fields of the remaining to commit (`REMAINING_FIELDS`). */
export const REMAINING: Fields = {
  node: [],
  task: [
    "progress",
    "finish",
    "finish_overdue",
    "awaiting_own_lines",
    "budgeted_amount",
    "reestimated_amount",
  ],
  line: [
    "quantity",
    "hours",
    "unit_disbursement",
    "budgeted_amount",
    "reestimated_amount",
    "previous_quantity",
    "previous_hours",
    "previous_unit_disbursement",
    "previous_reestimated_amount",
    "remaining_entry",
    "uses_inactive_object",
    "subproject_id",
    "subproject_label",
  ],
};

/** The tasks the grid of the planning reads (`PLANNING_KINDS`). */
export const PLANNING_KINDS = ["task"] as const;

/** The progress the remaining to commit shows unless its address says otherwise (`readProgress`). */
export const REMAINING_PROGRESS = ["started"] as const;

/**
 * A query string as the generated client sends it: a list joined by commas under its name, each
 * value escaped — the contract declares its lists `explode: false`, and the API reads them so.
 */
export function query(parameters: Readonly<Record<string, string | readonly string[]>>): string {
  const pairs = Object.entries(parameters).map(([name, value]) => {
    const values = typeof value === "string" ? [value] : value;
    return `${encodeURIComponent(name)}=${values.map((one) => encodeURIComponent(one)).join(",")}`;
  });
  return pairs.length === 0 ? "" : `?${pairs.join("&")}`;
}

/** The structures of the revision, which every grid reads first. */
function structures({ project, revision }: Place): Asked {
  return {
    name: "listCostStructures",
    path: `/projects/${project}/revisions/${revision}/structures`,
  };
}

/** The nodes of the main structure, as a grid asks them. */
function nodes(place: Place, parameters: Readonly<Record<string, string | readonly string[]>>) {
  const { project, revision, structure } = place;
  return {
    name: "listNodes",
    path: `/projects/${project}/revisions/${revision}/structures/${structure}/nodes${query(parameters)}`,
  };
}

/** A grid read, its structures first, then its nodes. */
function grid(
  name: string,
  parameters: (place: Place) => Record<string, string | readonly string[]>,
) {
  return {
    name,
    asks: (place: Place) => [structures(place), nodes(place, parameters(place))],
  };
}

/** What the browser of the measure types in the search of the estimate (`e2e/measure/steps.ts`). */
export const ESTIMATE_SEARCH = "revue";
/** The column the browser of the measure sorts the estimate by, ascending at the first click. */
export const ESTIMATE_SORT = "base_amount";

/** The readings a user of the load chooses among, each as likely. */
export const READINGS: readonly Reading[] = [
  grid("planning", () => ({ fields: fieldNames(PLANNING), kinds: PLANNING_KINDS })),
  grid("estimate", () => ({ fields: fieldNames(ESTIMATE) })),
  grid("estimate.filter", (place) => ({
    fields: fieldNames(ESTIMATE),
    work_package_id: place.workPackage,
  })),
  grid("estimate.sort", () => ({
    fields: fieldNames(ESTIMATE),
    sort_by: ESTIMATE_SORT,
    sort_order: "asc",
  })),
  grid("estimate.search", () => ({ fields: fieldNames(ESTIMATE), search: ESTIMATE_SEARCH })),
  grid("remaining", () => ({ fields: fieldNames(REMAINING), progress: REMAINING_PROGRESS })),
  {
    name: "workload",
    asks: ({ project }: Place) => [
      {
        name: "getProjectWorkload",
        path: `/projects/${project}/workload${query({ basis: "current_remaining" })}`,
      },
      { name: "listOrgNodes", path: "/reference/org-nodes" },
      {
        name: "listRevisions",
        path: `/projects/${project}/revisions${query({ status: "marked" })}`,
      },
    ],
  },
];

/** The task a user of the load writes, as the preparation read it. */
export interface Written {
  readonly node: string;
  readonly label: string;
}

/** An entry of the planning: its name, and the body of `updateTaskFacet` beside the counter. */
export interface Entry {
  readonly name: string;
  readonly body: (task: Written, count: number) => Readonly<Record<string, unknown>>;
}

/**
 * The entries a user of the load chooses among, each as likely: its label, marked with the count
 * of its entries, and its duration, seven or eight days in turn, which redates the task and its
 * successors.
 */
export const ENTRIES: readonly Entry[] = [
  { name: "label", body: (task, count) => ({ label: `${task.label} · ${String(count)}` }) },
  {
    name: "duration",
    body: (_task, count) => ({ duration: { value: count % 2 === 0 ? "7" : "8", unit: "d" } }),
  },
];

/** The status of a refusal by a state (`STATE_FORBIDS_OPERATION`, docs/api, `Problem`). */
const STATE_REFUSAL_STATUS = 409;
/** The code of that refusal. */
const STATE_REFUSAL_CODE = "STATE_FORBIDS_OPERATION";

/**
 * Whether an answer is the refusal a state makes — an entry on a revision marked (`revision_draft`),
 * the workload of the current revision of a project that has none (`current_remaining`) —, which
 * the marking of the measure causes: a 409 whose code is that of a state, not any 409.
 */
export function refusedByState(status: number, body: unknown): boolean {
  return (
    status === STATE_REFUSAL_STATUS &&
    typeof body === "object" &&
    body !== null &&
    "code" in body &&
    body.code === STATE_REFUSAL_CODE
  );
}

/** The path of the time facet of a task, which an entry writes (`updateTaskFacet`). */
export function taskPath({ project, revision, structure }: Place, task: Written): string {
  return `/projects/${project}/revisions/${revision}/structures/${structure}/nodes/${task.node}/task`;
}
