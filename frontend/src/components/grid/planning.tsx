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
 * computed (WF-PLA-0100): a column marked computed. The dates, the duration and the progress
 * are computed for some tasks only — automatic, summary —, which `computed_fields` names node by
 * node: reading them cell by cell is US-0150/L1 (#108), and until then no column claims them.
 *
 * The Gantt comes to the right of this grid, row for row (US-0220/L2, #114): its columns keep to
 * the width the mock-up gives the grid beside it.
 */
import { Contrast, Zap } from "lucide-react";

import { type GridConfig, sortColumns } from "./columns";
import {
  LABEL_COLUMN,
  NODE_TREE,
  type Node,
  type NodeKind,
  nodeKey,
  nodeNumber,
  type NodeSortColumn,
  type NodeTotals,
} from "./nodes";
import {
  DaysCell,
  FloatCell,
  PredecessorsCell,
  ProgressCell,
  SchedulingModeCell,
} from "./planning-cells";

/** What the grid of the planning asks the server to render: the tasks, not the lines. */
export const PLANNING_KINDS: readonly NodeKind[] = ["task"];

/** The grid of the planning. */
export const PLANNING_GRID: GridConfig<Node, NodeSortColumn, NodeTotals> = {
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
      key: "duration_days",
      label: "duration",
      format: "decimal",
      width: 64,
      sortBy: "duration_days",
      value: (node) => node.task?.duration_days.toString(),
      render: (node) => <DaysCell days={node.task?.duration_days} />,
    },
    {
      key: "start_date",
      label: "startDate",
      format: "date",
      width: 88,
      sortBy: "start_date",
      value: (node) => node.task?.start_date,
    },
    {
      key: "finish_date",
      label: "finishDate",
      format: "date",
      width: 88,
      sortBy: "finish_date",
      value: (node) => node.task?.finish_date,
    },
    {
      key: "progress",
      label: "progress",
      format: "text",
      align: "center",
      width: 44,
      icon: Contrast,
      sortBy: "progress",
      value: (node) => node.task?.progress,
      render: (node) => <ProgressCell node={node} />,
    },
    {
      key: "total_float_days",
      label: "totalFloat",
      format: "decimal",
      width: 72,
      computed: true,
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
