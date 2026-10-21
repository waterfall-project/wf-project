// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the planning (WF-PLA-0080), after the validated mock-up: the
 * common tree of a structure (`listNodes`) read without its lines — `kinds=task`, which chooses
 * what the grid renders and leaves the totals as they are —, each task numbered, indented and
 * marked by the icon of its nature; its label, its description, its scheduling mode, its duration,
 * its dates, its progress, the physical progress of a summary, its total float with the mark of the
 * critical path, and its predecessors — the columns WF-PLA-0080 names, in the order of the contract
 * (`NodeColumn`) —, and the post or the lot of the work breakdown the task bears, by the label the
 * server resolves (WF-PLA-0170); then the Gantt, row for row (`GanttCell`). The same component as the
 * grid of the estimate (`estimate.ts`): another configuration.
 *
 * Each column but the Gantt shows the column of the contract of the same name, and none sorts: the
 * grid is a tree, whose rows keep the order of the plan (§3.4, WF-IHM-0060) — no header offers a
 * sort, and the address asks none. The total float and the physical progress are always computed
 * (WF-PLA-0100, WF-IND-0060): columns computed whole. The dates, the duration and the progress are
 * computed for some tasks only — automatic, summary —, which `computed_fields` names node by
 * node: those cells are computed, the others entered (WF-IHM-0030).
 *
 * The Gantt comes to the right of this grid, row for row (US-0220/L2): its columns keep to the width
 * the mock-up gives the grid beside it — the dates a little wider, for the mark of a computed date
 * before them —, and the Gantt widens with its column.
 */
import { Contrast, Zap } from "lucide-react";

import { GanttAxis, GanttCell } from "@/components/gantt/gantt";

import type { Outcome } from "@/api/problem";

import {
  type Choice,
  type ComputedCells,
  type GridColumn,
  type GridConfig,
  type RowsWritten,
  sortColumns,
} from "./columns";
import { COMPUTED_FLOAT, computedWhereNamed } from "./computed-nodes";
import {
  type AnyNodeFields,
  LABEL_COLUMN,
  NODE_TREE,
  type NodeKind,
  nodeFresher,
  nodeKey,
  nodeNumber,
  type NodeSortColumn,
  type NodeTotals,
  type RowOf,
} from "./nodes";
import type { ChoiceOption } from "./row-choices";
import {
  type AttachmentChange,
  attachmentChange,
  borne,
  type BreakdownItem,
} from "./planning-attachment";
import {
  DurationCell,
  FloatCell,
  PhysicalProgressCell,
  PredecessorsCell,
  ProgressCell,
  SchedulingModeCell,
  TrackingCell,
} from "./planning-cells";

/** What the grid of the planning asks the server to render: the tasks, not the lines. */
export const PLANNING_KINDS: readonly NodeKind[] = ["task"];

/**
 * What the columns of the planning read of a node, beyond what every grid reads: its
 * predecessors, and the schedule of its task. The page hands the grid these alone
 * (`projectNodes`).
 */
export const PLANNING_FIELDS = {
  node: ["predecessors"],
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
    "order_item_id",
    "work_package_id",
    "work_breakdown_label",
    "tracking",
  ],
  line: [],
} as const satisfies AnyNodeFields;

/** A node as the grid of the planning reads it. */
export type PlanningNode = RowOf<typeof PLANNING_FIELDS>;

/**
 * The cells of the physical progress, computed in every task that bears it — a summary
 * (WF-IND-0060) —: a leaf bears none, and its cell is empty.
 */
const COMPUTED_PHYSICAL_PROGRESS: ComputedCells<PlanningNode> = {
  whole: true,
  in: (node) => node.task?.physical_progress !== undefined && node.task.physical_progress !== null,
  field: () => "task.physical_progress",
};

/** The grid of the planning. */
export const PLANNING_GRID: GridConfig<PlanningNode, NodeSortColumn, NodeTotals> = {
  key: "planning",
  searched: true,
  sorts: false,
  name: "planning",
  rowKey: nodeKey,
  fresher: nodeFresher,
  rowNumber: nodeNumber,
  tree: NODE_TREE,
  columns: [
    { ...LABEL_COLUMN, width: 240 },
    {
      key: "description",
      label: "description",
      format: "text",
      width: 120,
      contract: "description",
      value: (node) => node.task?.description,
    },
    {
      key: "scheduling_mode",
      label: "schedulingMode",
      format: "text",
      align: "center",
      width: 44,
      icon: Zap,
      contract: "scheduling_mode",
      value: (node) => node.task?.scheduling_mode,
      render: (node) => <SchedulingModeCell node={node} />,
    },
    {
      key: "duration",
      label: "duration",
      format: "decimal",
      width: 64,
      computed: computedWhereNamed("task.duration"),
      contract: "duration",
      // The value in its unit (WF-PLA-0160): the cell writes the unit after it.
      value: (node) => node.task?.duration.value,
      render: (node) => <DurationCell duration={node.task?.duration} />,
    },
    // The start and the finish of a task are a date and the hours of work elapsed that day
    // (WF-DAT-0100); the grid shows the date.
    {
      key: "start",
      label: "startDate",
      format: "date",
      width: 100,
      computed: computedWhereNamed("task.start"),
      contract: "start",
      value: (node) => node.task?.start?.date,
    },
    {
      key: "finish",
      label: "finishDate",
      format: "date",
      width: 100,
      computed: computedWhereNamed("task.finish"),
      contract: "finish",
      value: (node) => node.task?.finish?.date,
    },
    {
      key: "progress",
      label: "progress",
      format: "text",
      align: "center",
      width: 44,
      icon: Contrast,
      computed: computedWhereNamed("task.progress"),
      contract: "progress",
      value: (node) => node.task?.progress,
      render: (node) => <ProgressCell node={node} />,
    },
    {
      key: "physical_progress",
      label: "physicalProgress",
      format: "percent",
      width: 72,
      computed: COMPUTED_PHYSICAL_PROGRESS,
      contract: "physical_progress",
      value: (node) => node.task?.physical_progress?.value,
      render: (node) => <PhysicalProgressCell node={node} />,
    },
    {
      key: "total_float",
      label: "totalFloat",
      format: "decimal",
      width: 72,
      computed: COMPUTED_FLOAT,
      contract: "total_float",
      value: (node) => node.task?.total_float?.value,
      render: (node) => <FloatCell node={node} />,
    },
    {
      key: "predecessors",
      label: "predecessors",
      format: "text",
      width: 104,
      contract: "predecessors",
      // Never shown: the cell renders the links, named by row number.
      value: () => undefined,
      render: (node) => <PredecessorsCell node={node} />,
    },
    // The post or the lot the task bears, by the label the server resolves (WF-PLA-0170).
    {
      key: "work_breakdown",
      label: "attachment",
      format: "text",
      width: 160,
      contract: "work_breakdown",
      value: (node) => node.task?.work_breakdown_label,
    },
    // The timelines the task is inscribed to (WF-PLA-0060), by their names; hidden until the account
    // shows it, and read only: they are chosen in the menu of the cell (`row-choices.tsx`).
    {
      key: "timelines",
      label: "timelines",
      format: "text",
      width: 160,
      hidden: true,
      // Never shown: the cell renders the names of the timelines (`planningGrid`).
      value: () => undefined,
      render: (node) => <TrackingCell node={node} names={new Map()} />,
    },
    {
      key: "gantt",
      label: "gantt",
      format: "text",
      width: 400,
      // No column of the contract, nor a value shown: the cell draws the row of the task.
      value: () => undefined,
      render: (node) => <GanttCell row={node} />,
      axis: (width) => <GanttAxis width={width} />,
    },
  ],
};

/** The columns of the contract the grid of the planning sorts by: none (§3.4, WF-IHM-0060). */
export const PLANNING_SORT_COLUMNS = sortColumns(PLANNING_GRID);

/**
 * How the grid of the planning writes the attachment of a task: the posts and the lots it is chosen
 * among, each named by its kind — a function, never the list (défaut n° 14) —, and the write of the
 * fields it changes, with the row the server answers.
 */
export interface PlanningAttachment {
  readonly items: ReadonlyMap<string, BreakdownItem>;
  readonly choices: () => readonly Choice[];
  readonly write: (
    node: PlanningNode,
    change: AttachmentChange,
  ) => Promise<Outcome<RowsWritten<PlanningNode, NodeTotals>>>;
}

/** Whether the node accepts the attachment, which it says (`editable_fields`, #219). */
function attachable(node: PlanningNode): boolean {
  return (
    node.editable_fields.includes("task.order_item_id") &&
    node.editable_fields.includes("task.work_package_id")
  );
}

/** The column of the attachment, entered through `attachment`. */
function attachmentColumn(
  column: GridColumn<PlanningNode, NodeSortColumn, NodeTotals>,
  attachment: PlanningAttachment,
): GridColumn<PlanningNode, NodeSortColumn, NodeTotals> {
  return {
    ...column,
    entry: {
      kind: { type: "choice", choices: attachment.choices, nullable: true },
      // A task whose item the work breakdown read does not know is not entered, so that no first
      // choice is written for it unseen.
      in: (node) => {
        const id = borne(node.task);
        return attachable(node) && (id === null || attachment.items.has(id));
      },
      value: (node) => borne(node.task),
      write: (node, value) =>
        attachment.write(
          node,
          attachmentChange(node.task, value === null ? undefined : attachment.items.get(value)),
        ),
    },
  };
}

/** The column of the timelines, naming each of the project by its label. */
function timelinesColumn(
  column: GridColumn<PlanningNode, NodeSortColumn, NodeTotals>,
  timelines: readonly ChoiceOption[],
): GridColumn<PlanningNode, NodeSortColumn, NodeTotals> {
  const names = new Map(timelines.map((timeline) => [timeline.id, timeline.label]));
  return { ...column, render: (node) => <TrackingCell node={node} names={names} /> };
}

/**
 * The grid of the planning: the attachment of its tasks entered through `attachment` — a revision
 * whose planning may be entered (`edit_planning`), and the work breakdown read whole —; none, and the
 * grid is read only. The timelines of the project name the inscriptions of its tasks.
 */
export function planningGrid(
  attachment?: PlanningAttachment,
  timelines: readonly ChoiceOption[] = [],
): GridConfig<PlanningNode, NodeSortColumn, NodeTotals> {
  return {
    ...PLANNING_GRID,
    columns: PLANNING_GRID.columns.map((column) => {
      if (column.key === "timelines") {
        return timelinesColumn(column, timelines);
      }
      return attachment !== undefined && column.key === "work_breakdown"
        ? attachmentColumn(column, attachment)
        : column;
    }),
  };
}
