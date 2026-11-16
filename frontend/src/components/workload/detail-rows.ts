// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the detail of the workload reads of the plan (WF-DEV-0090, US-2040): one row for each role,
 * in the order of the API, and under it one row for each of its tasks, in the order the API gives
 * them — their start, then the plan (`roles[].tasks`) —; the hours of each month as the API gives
 * them, a month the API leaves out of a role or of a task left blank, never filled with a zero; the
 * hours of a task, which the API sums; none for a role, which the API does not sum. The totals of
 * the months are the plan's (`monthly_totals`). Nothing is summed, ordered nor filtered here
 * (WF-ARC-0070).
 *
 * The page reads them on the server and hands them to the grid as they are: data only, the link of
 * each task to its row in the planning grid already written (`TaskLink`). No module here is a client
 * one.
 */
import type { components } from "@/api/generated/schema";

/** The workload of a project, as the API computes it. */
type WorkloadPlan = components["schemas"]["WorkloadPlan"];

/** A task of the detail of a role, as the API gives it. */
export type WorkloadTask = components["schemas"]["WorkloadTask"];

/** The key under which the account keeps the settings of the grid of the detail. */
export const DETAIL_GRID_KEY = "workload_detail";

/** The hours of a row, by the month the API names (`2026-06`); a month without load is absent. */
export type MonthHours = Readonly<Record<string, string>>;

/** A row of the detail: a role, or a task under it. */
export interface DetailRow {
  /** The identity of the row: the role, or the role and the task, which may be under several roles. */
  readonly key: string;
  /** The role a task is under; none for a role. */
  readonly parent: string | null;
  readonly kind: "role" | "task";
  readonly label: string;
  /** The row of a task in the numbering of the whole structure; none for a role. */
  readonly rowNumber?: string;
  /** The start and the finish of a task, its date as the API gives it; none for a role. */
  readonly start?: string;
  readonly finish?: string;
  /** The hours of a task for its role, as the API sums them; none for a role. */
  readonly hours?: string;
  readonly months: MonthHours;
  /** Where the task is shown and aimed at in the planning grid; none for a role, or no link. */
  readonly href?: string;
}

/** The hours of each month of the plan, as the API sums them (`monthly_totals`). */
export type DetailTotals = MonthHours;

/** The detail of the workload, as the grid reads it. */
export interface WorkloadDetail {
  readonly rows: readonly DetailRow[];
  /** The months of the plan, ascending and without gaps (`monthly_totals`): one column each. */
  readonly months: readonly string[];
  readonly totals: DetailTotals;
}

/** The address of a task in the planning grid, if the session may follow it there. */
export type TaskLink = (task: WorkloadTask) => string | undefined;

/** The hours of a list of months of the API, by their month. */
function byMonth(
  months: readonly { readonly month: string; readonly hours: string }[],
): MonthHours {
  return Object.fromEntries(months.map(({ month, hours }) => [month, hours]));
}

/** The row of a task under its role. */
function taskRow(role: string, task: WorkloadTask, link: TaskLink): DetailRow {
  const href = link(task);
  return {
    key: `${role}:${task.node_id}`,
    parent: role,
    kind: "task",
    label: task.label,
    rowNumber: task.row_number.toString(),
    start: task.start.date,
    finish: task.finish.date,
    hours: task.hours,
    months: byMonth(task.months),
    ...(href === undefined ? {} : { href }),
  };
}

/**
 * The detail of a plan: each role, then its tasks, in the order of the API; the months of the plan
 * and their totals, as the API gives them.
 */
export function workloadDetail(plan: WorkloadPlan, link: TaskLink): WorkloadDetail {
  return {
    rows: plan.roles.flatMap((role) => [
      {
        key: role.resource_role_id,
        parent: null,
        kind: "role" as const,
        label: role.label,
        months: byMonth(role.months),
      },
      ...role.tasks.map((task) => taskRow(role.resource_role_id, task, link)),
    ]),
    months: plan.monthly_totals.map(({ month }) => month),
    totals: byMonth(plan.monthly_totals),
  };
}

/**
 * The plan without the detail of its roles, which the chart does not read: a thousand tasks are not
 * written into the page twice.
 */
export function withoutTasks(plan: WorkloadPlan): WorkloadPlan {
  return { ...plan, roles: plan.roles.map((role) => ({ ...role, tasks: [] })) };
}
