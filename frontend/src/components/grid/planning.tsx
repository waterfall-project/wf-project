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
 * node: those cells are computed, traversed and never entered, the others entered (WF-IHM-0030,
 * WF-PLA-0020).
 *
 * Where the structure lists `edit_planning`, a task is entered from the keyboard alone, cell by cell
 * (US-0470, WF-IHM-0040), by `updateTaskFacet`: its label, its description, its mode, its duration
 * with the suffix of its unit (WF-PLA-0160), the start and the finish of a task in manual mode, and
 * its attachment — each where the node names its field among those it accepts (`editable_fields`),
 * never by its mode nor its nature.
 *
 * The Gantt comes to the right of this grid, row for row (US-0220/L2): its columns keep to the width
 * the mock-up gives the grid beside it — the dates a little wider, for the mark of a computed date
 * before them —, and the Gantt widens with its column.
 */
import { Contrast, Zap } from "lucide-react";

import { GanttAxis, GanttCell } from "@/components/gantt/gantt";

import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";

import { durationEntered, durationOf } from "./cell-values";
import {
  type CellValue,
  type Choice,
  type ComputedCells,
  type DurationUnit,
  type EntryKind,
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
import { attachmentChange, borne, type BreakdownItem } from "./planning-attachment";
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

/** A field of a facet a node may accept, as the contract names it. */
type EditableField = components["schemas"]["EditableField"];

/** The scheduling mode of a task (WF-PLA-0020). */
type SchedulingMode = components["schemas"]["SchedulingMode"];

/**
 * The modes of a task, in the order of the contract: every one, one it adds failing the type check
 * here (défaut n° 4).
 */
const SCHEDULING_MODES = {
  automatic: true,
  manual: true,
} as const satisfies Record<SchedulingMode, true>;

/** Whether a value chosen is a mode of a task. */
function isMode(value: string | null): value is SchedulingMode {
  return value !== null && Object.hasOwn(SCHEDULING_MODES, value);
}

/** The modes of a task, in the order of the contract. */
const MODES: readonly SchedulingMode[] = Object.keys(SCHEDULING_MODES).filter(isMode);

/**
 * The fields of a task an entry writes: the cell entered, nothing else (#178) — and, for the
 * attachment, the other item set to `null` in the same write (`attachmentChange`).
 */
export type TaskChange = Partial<
  Pick<
    components["schemas"]["TaskFacetUpdate"],
    | "label"
    | "description"
    | "scheduling_mode"
    | "duration"
    | "start"
    | "finish"
    | "order_item_id"
    | "work_package_id"
  >
>;

/**
 * How the grid of the planning writes the attachment of a task: the posts and the lots it is chosen
 * among, each named by its kind — a function, never the list (défaut n° 14).
 */
export interface PlanningAttachment {
  readonly items: ReadonlyMap<string, BreakdownItem>;
  readonly choices: () => readonly Choice[];
}

/**
 * How the grid of the planning writes the cells of a task (US-0470): the fields it changes, with the
 * row the server answers; the names of the modes and the suffixes of the units of a duration in the
 * language of the interface; the attachment, where the work breakdown was read.
 */
export interface PlanningWrites {
  readonly task: (
    node: PlanningNode,
    change: TaskChange,
  ) => Promise<Outcome<RowsWritten<PlanningNode, NodeTotals>>>;
  /** The modes a task is set to, each named in the language. */
  readonly modes: (mode: SchedulingMode) => string;
  /** The suffix of a unit of a duration in the language (`enums.DurationUnit`). */
  readonly suffix: (unit: DurationUnit) => string;
  /** A duration written as the cell shows it: its value formatted, and its suffix. */
  readonly written: (value: string, unit: DurationUnit) => string;
  readonly attachment?: PlanningAttachment | undefined;
}

/**
 * How a column of a task is entered: what it takes, the field the node must accept for it, the value
 * an entry starts from, and what a value validated writes, from the row it is written from.
 */
interface TaskEntered {
  readonly kind: EntryKind;
  readonly field: EditableField;
  readonly value: (node: PlanningNode) => CellValue;
  readonly change: (task: PlanningTask, value: string | null) => TaskChange;
}

/** The task of a node of the planning, which a cell of a task is entered from. */
type PlanningTask = NonNullable<PlanningNode["task"]>;

/**
 * The start or the finish of a task, entered as a date: it keeps the hours of work the task had at
 * its former date, not those of the new day (WF-DAT-0100, #1244) — a task with no date there yet
 * has none, and the date starts at hour 0, its first —; the grid shows the date alone.
 */
function instant(
  field: "start" | "finish",
): (task: PlanningTask, value: string | null) => TaskChange {
  return (task, value) => ({
    [field]: value === null ? null : { date: value, hours: task[field]?.hours ?? "0" },
  });
}

/** The columns of a task that take an entry, by the key of their column. */
function taskColumns(writes: PlanningWrites): Readonly<Record<string, TaskEntered>> {
  const modes = MODES.map((mode) => ({ id: mode, label: writes.modes(mode), active: true }));
  return {
    // The contract takes a label of 1 to 300 characters.
    label: {
      kind: { type: "text", maxLength: 300 },
      field: "task.label",
      value: (node) => node.task?.label,
      change: (_, value) => ({ label: value ?? "" }),
    },
    // A description the contract does not bound, emptied to none.
    description: {
      kind: { type: "text", maxLength: undefined, nullable: true },
      field: "task.description",
      value: (node) => node.task?.description,
      change: (_, value) => ({ description: value }),
    },
    scheduling_mode: {
      kind: { type: "choice", choices: () => modes, nullable: false },
      field: "task.scheduling_mode",
      value: (node) => node.task?.scheduling_mode,
      change: (_, value) => (isMode(value) ? { scheduling_mode: value } : {}),
    },
    // A duration with the suffix of its unit, kept in that unit (WF-PLA-0160).
    duration: {
      kind: { type: "duration", suffix: writes.suffix, written: writes.written },
      field: "task.duration",
      value: (node) => durationEntered(node.task?.duration),
      change: (_, value) => {
        const duration = value === null ? undefined : durationOf(value);
        return duration === undefined ? {} : { duration };
      },
    },
    start: {
      kind: { type: "date" },
      field: "task.start",
      value: (node) => node.task?.start?.date,
      change: instant("start"),
    },
    finish: {
      kind: { type: "date" },
      field: "task.finish",
      value: (node) => node.task?.finish?.date,
      change: instant("finish"),
    },
  };
}

/**
 * A column of a task entered through `writes`, where its node accepts the field — which the node
 * says, never the grid by its mode or its nature (#219) — and the server does not compute it there:
 * a computed cell is traversed, and refuses the entry (WF-IHM-0030, WF-PLA-0020). A node read
 * without its task refuses it too: no change is made up for a task the grid did not read.
 */
function taskColumn(
  column: GridColumn<PlanningNode, NodeSortColumn, NodeTotals>,
  spec: TaskEntered,
  writes: PlanningWrites,
): GridColumn<PlanningNode, NodeSortColumn, NodeTotals> {
  return {
    ...column,
    entry: {
      kind: spec.kind,
      in: (node) =>
        node.task != null &&
        node.editable_fields.includes(spec.field) &&
        column.computed?.in(node) !== true,
      value: spec.value,
      // A node without its task never gets here, its cells refusing the entry (`in`).
      write: (node, value) =>
        writes.task(node, node.task == null ? {} : spec.change(node.task, value)),
    },
  };
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
  writes: PlanningWrites,
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
        writes.task(
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
 * The grid of the planning: the cells of its tasks entered through `writes` — a structure whose
 * planning may be entered (`edit_planning`) —, its label, its description, its mode, its duration
 * with its unit, the dates of a manual task, and the attachment where the work breakdown was read
 * whole; none, and the grid is read only. The timelines of the project name the inscriptions of its
 * tasks.
 */
export function planningGrid(
  writes?: PlanningWrites,
  timelines: readonly ChoiceOption[] = [],
): GridConfig<PlanningNode, NodeSortColumn, NodeTotals> {
  const specs = writes === undefined ? {} : taskColumns(writes);
  return {
    ...PLANNING_GRID,
    columns: PLANNING_GRID.columns.map((column) => {
      if (column.key === "timelines") {
        return timelinesColumn(column, timelines);
      }
      if (writes === undefined) {
        return column;
      }
      const spec = specs[column.key];
      if (spec !== undefined) {
        return taskColumn(column, spec, writes);
      }
      return writes.attachment !== undefined && column.key === "work_breakdown"
        ? attachmentColumn(column, writes.attachment, writes)
        : column;
    }),
  };
}
