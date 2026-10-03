// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the planning (WF-PLA-0080), after the validated mock-up: the
 * common tree of a structure (`listNodes`) read without its lines — `kinds=task`, which chooses
 * what the grid renders and leaves the totals as they are —, each task numbered, indented and
 * marked by the icon of its nature; its label, its scheduling mode, its duration, its dates,
 * its progress, its total float with the mark of the critical path, and its predecessors. The
 * same component as the grid of the estimate (`estimate.ts`): another configuration.
 *
 * Each column sorts by the column of the contract of the same name. The total float is always
 * computed (WF-PLA-0100): a column computed whole. The dates, the duration and the progress are
 * computed for some tasks only — automatic, summary —, which `computed_fields` names node by
 * node: those cells are computed, the others entered (WF-IHM-0030).
 *
 * The Gantt comes to the right of this grid, row for row (US-0220/L2, #114): its columns keep to
 * the width the mock-up gives the grid beside it — the dates a little wider, for the mark of a
 * computed date before them.
 */
import { Contrast, Zap } from "lucide-react";

import { type GridConfig, sortColumns } from "./columns";
import { COMPUTED_FLOAT, computedWhereNamed } from "./computed-nodes";
import {
  type AnyNodeFields,
  LABEL_COLUMN,
  NODE_TREE,
  type NodeKind,
  nodeKey,
  nodeNumber,
  type NodeSortColumn,
  type NodeTotals,
  type RowOf,
} from "./nodes";
import {
  DurationCell,
  FloatCell,
  PredecessorsCell,
  ProgressCell,
  SchedulingModeCell,
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
    "scheduling_mode",
    "duration",
    "start",
    "finish",
    "progress",
    "total_float_days",
    "is_critical",
  ],
  line: [],
} as const satisfies AnyNodeFields;

/** A node as the grid of the planning reads it. */
export type PlanningNode = RowOf<typeof PLANNING_FIELDS>;

/** The grid of the planning. */
export const PLANNING_GRID: GridConfig<PlanningNode, NodeSortColumn, NodeTotals> = {
  key: "planning",
  name: "planning",
  rowKey: nodeKey,
  rowNumber: nodeNumber,
  tree: NODE_TREE,
  columns: [
    { ...LABEL_COLUMN, width: 240 },
    {
      key: "scheduling_mode",
      label: "schedulingMode",
      format: "text",
      align: "center",
      width: 44,
      icon: Zap,
      sortBy: "scheduling_mode",
      value: (node) => node.task?.scheduling_mode,
      render: (node) => <SchedulingModeCell node={node} />,
    },
    {
      key: "duration",
      label: "duration",
      format: "decimal",
      width: 64,
      computed: computedWhereNamed("task.duration"),
      sortBy: "duration",
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
      sortBy: "start",
      value: (node) => node.task?.start?.date,
    },
    {
      key: "finish",
      label: "finishDate",
      format: "date",
      width: 100,
      computed: computedWhereNamed("task.finish"),
      sortBy: "finish",
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
      sortBy: "progress",
      value: (node) => node.task?.progress,
      render: (node) => <ProgressCell node={node} />,
    },
    {
      key: "total_float_days",
      label: "totalFloat",
      format: "decimal",
      width: 72,
      computed: COMPUTED_FLOAT,
      sortBy: "total_float_days",
      value: (node) => node.task?.total_float_days?.toString(),
      render: (node) => <FloatCell node={node} />,
    },
    {
      key: "predecessors",
      label: "predecessors",
      format: "text",
      width: 104,
      sortBy: "predecessors",
      // The accessor of the sort alone: the cell renders the links, named by row number.
      value: (node) => node.predecessors?.length.toString(),
      render: (node) => <PredecessorsCell node={node} />,
    },
  ],
};

/** The columns of the contract the grid of the planning sorts by. */
export const PLANNING_SORT_COLUMNS = sortColumns(PLANNING_GRID);
