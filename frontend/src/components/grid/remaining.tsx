// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the remaining to commit (WF-RAE-0040): the common tree of a
 * structure (`listNodes`), its tasks and the lines they bear, each row numbered and marked by the
 * icon of its nature; the progress of a task, an icon named for its state — a task is completed or
 * it is not, and no percentage is entered anywhere (US-0230) —, its finish, never entered here, and
 * the mark of a task started whose finish is past the date of calculation, which the server says
 * (`finish_overdue`); of a line, its budgeted amount, its figures — quantity, effort, unit
 * disbursement — and its amount re-estimated at the previous remaining to commit, and its figures
 * and its amount re-estimated now (WF-RAE-0040, #424), the three amounts computed by the server
 * and never entered, the figures at the previous remaining to commit kept by the server and never
 * entered either — none before the first review. The totals are those of the answer: the hours and
 * the amounts of the lines retained.
 *
 * The re-estimation is entered on the figures (WF-RAE-0040, WF-DEV-0020), each written alone by
 * `setLineRemaining`: where the node accepts the field (`editable_fields`) and does not compute it
 * (`computed_fields`), and where the line says it takes a re-estimation (`remaining_entry`) — the
 * lines of a task completed do not —, never deduced here from the progress of its task.
 */
import { CalendarX2, Contrast } from "lucide-react";

import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";

import {
  type ComputedCells,
  type EntryKind,
  type GridColumn,
  type GridConfig,
  type RowsWritten,
  sortColumns,
} from "./columns";
import { computedAmount, computedWhereNamed } from "./computed-nodes";
import {
  type AnyNodeFields,
  type GridNode,
  LABEL_COLUMN,
  NODE_TREE,
  nodeKey,
  nodeNumber,
  type NodeSortColumn,
  type NodeTotals,
  type RowOf,
} from "./nodes";
import { ProgressCell } from "./planning-cells";
import { OverdueCell } from "./remaining-cells";

/**
 * What the columns of the remaining to commit read of a node, beyond what every grid reads: the
 * progress, the finish and its overrun of a task, and its amounts; the figures of a line, its
 * amounts, and whether it takes a re-estimation. The page asks for these alone (`fields`) and
 * hands the grid these alone (`projectNodes`).
 */
export const REMAINING_FIELDS = {
  node: [],
  task: ["progress", "finish", "finish_overdue", "budgeted_amount", "reestimated_amount"],
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
  ],
} as const satisfies AnyNodeFields;

/** A node as the grid of the remaining to commit reads it. */
export type RemainingNode = RowOf<typeof REMAINING_FIELDS>;

/**
 * The cells of the amount re-estimated at the previous remaining to commit: computed in every
 * line, a task bearing none (`EstimateLineFacet.previous_reestimated_amount`).
 */
const COMPUTED_PREVIOUS: ComputedCells<GridNode> = {
  whole: true,
  in: (node) => node.kind === "estimate_line",
  field: () => "estimate_line.previous_reestimated_amount",
};

/** The grid of the remaining to commit, read only. */
export const REMAINING_GRID: GridConfig<RemainingNode, NodeSortColumn, NodeTotals> = {
  key: "remaining",
  searched: true,
  name: "remaining",
  rowKey: nodeKey,
  rowNumber: nodeNumber,
  tree: NODE_TREE,
  columns: [
    LABEL_COLUMN,
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
    // The finish of a task, a date and the hours of work elapsed that day (WF-DAT-0100): the grid
    // shows the date, and enters none (WF-RAE-0040).
    {
      key: "finish",
      label: "finishDate",
      format: "date",
      width: 100,
      sortBy: "finish",
      value: (node) => node.task?.finish?.date,
    },
    // A narrow column headed by the icon of its mark; the server sorts by no such column.
    {
      key: "finish_overdue",
      label: "finishOverdue",
      format: "text",
      align: "center",
      width: 44,
      icon: CalendarX2,
      value: () => undefined,
      render: (node) => <OverdueCell node={node} />,
    },
    {
      key: "budgeted_amount",
      label: "budgetedAmount",
      format: "money",
      width: 128,
      computed: computedAmount("budgeted_amount"),
      sortBy: "budgeted_amount",
      value: (node) => node.task?.budgeted_amount ?? node.estimate_line?.budgeted_amount,
      total: (totals) => totals.budgeted_amount,
    },
    // The figures at the previous remaining to commit, kept by the server and never entered; left
    // out by the projection or null alike when the line has none.
    {
      key: "previous_quantity",
      label: "previousQuantity",
      format: "decimal",
      width: 96,
      sortBy: "previous_quantity",
      value: (node) => node.estimate_line?.previous_quantity ?? null,
    },
    {
      key: "previous_hours",
      label: "previousHours",
      format: "decimal",
      width: 112,
      sortBy: "previous_hours",
      value: (node) => node.estimate_line?.previous_hours ?? null,
    },
    {
      key: "previous_unit_disbursement",
      label: "previousUnitDisbursement",
      format: "money",
      width: 128,
      sortBy: "previous_unit_disbursement",
      value: (node) => node.estimate_line?.previous_unit_disbursement ?? null,
    },
    {
      key: "previous_reestimated_amount",
      label: "previousReestimatedAmount",
      format: "money",
      width: 128,
      computed: COMPUTED_PREVIOUS,
      sortBy: "previous_reestimated_amount",
      value: (node) => node.estimate_line?.previous_reestimated_amount,
    },
    {
      key: "quantity",
      label: "quantity",
      format: "decimal",
      width: 72,
      computed: computedWhereNamed("estimate_line.quantity"),
      sortBy: "quantity",
      value: (node) => node.estimate_line?.quantity,
    },
    {
      key: "hours",
      label: "hours",
      format: "decimal",
      width: 96,
      computed: computedWhereNamed("estimate_line.hours"),
      sortBy: "hours",
      value: (node) => node.estimate_line?.hours,
      total: (totals) => totals.hours,
    },
    {
      key: "unit_disbursement",
      label: "unitDisbursement",
      format: "money",
      width: 128,
      computed: computedWhereNamed("estimate_line.unit_disbursement"),
      sortBy: "unit_disbursement",
      value: (node) => node.estimate_line?.unit_disbursement,
    },
    {
      key: "reestimated_amount",
      label: "reestimatedAmount",
      format: "money",
      width: 128,
      computed: computedAmount("reestimated_amount"),
      sortBy: "reestimated_amount",
      value: (node) => node.task?.reestimated_amount ?? node.estimate_line?.reestimated_amount,
      total: (totals) => totals.reestimated_amount,
    },
  ],
};

/** The columns of the contract the grid of the remaining to commit sorts by. */
export const REMAINING_SORT_COLUMNS = sortColumns(REMAINING_GRID);

/** What a write of the grid of the remaining to commit answers, as the grid reads it. */
export type RemainingWritten = RowsWritten<RemainingNode, NodeTotals>;

/** The figures of a re-estimation an entry writes: the cell entered, nothing else. */
export type RemainingBasis = components["schemas"]["RemainingUpdate"]["reestimated_amount_basis"];

/**
 * How the grid of the remaining to commit writes a cell: a figure of a line re-estimated, the row
 * answered as the grid reads it; and how it reads anew the totals of a reading the writes do not
 * answer them for — none, they do.
 */
export interface RemainingWrites {
  readonly line: (node: RemainingNode, basis: RemainingBasis) => Promise<Outcome<RemainingWritten>>;
  readonly totals?: (() => Promise<Outcome<NodeTotals>>) | undefined;
}

/** A field of a facet a node may accept, as the contract names it. */
type EditableField = components["schemas"]["EditableField"];

/**
 * How a figure of a line is entered: what it takes, the field the node must accept, what it
 * writes.
 */
interface Entered {
  readonly kind: EntryKind;
  readonly field: EditableField;
  readonly basis: (value: string | null) => RemainingBasis;
}

/** The figures of a line a re-estimation is entered on, by the key of their column. */
const ENTERED: Readonly<Record<string, Entered>> = {
  quantity: {
    kind: { type: "decimal", nullable: false },
    field: "estimate_line.quantity",
    basis: (value) => (value === null ? {} : { quantity: value }),
  },
  hours: {
    kind: { type: "decimal", nullable: true },
    field: "estimate_line.hours",
    basis: (value) => ({ hours: value }),
  },
  unit_disbursement: {
    kind: { type: "money", nullable: true },
    field: "estimate_line.unit_disbursement",
    basis: (value) => ({ unit_disbursement: value }),
  },
};

/**
 * Whether a line takes the re-estimation of a figure: it says it takes one (`remaining_entry`), and
 * its node accepts the field.
 */
function takes(node: RemainingNode, field: EditableField): boolean {
  return (
    node.estimate_line?.remaining_entry.is_available === true &&
    node.editable_fields.includes(field)
  );
}

/** A column of the remaining to commit, entered through `writes` when it is a figure of a line. */
function entered(
  column: GridColumn<RemainingNode, NodeSortColumn, NodeTotals>,
  writes: RemainingWrites,
): GridColumn<RemainingNode, NodeSortColumn, NodeTotals> {
  const spec = ENTERED[column.key];
  if (spec === undefined) {
    return column;
  }
  return {
    ...column,
    entry: {
      kind: spec.kind,
      in: (node) => takes(node, spec.field) && column.computed?.in(node) !== true,
      value: column.value,
      write: (node, value) => writes.line(node, spec.basis(value)),
    },
  };
}

/**
 * The grid of the remaining to commit: its figures re-estimated through `writes`; none, and the
 * grid is read only. It takes no paste: the contract pastes in the estimate alone.
 */
export function remainingGrid(
  writes?: RemainingWrites,
): GridConfig<RemainingNode, NodeSortColumn, NodeTotals> {
  if (writes === undefined) {
    return REMAINING_GRID;
  }
  return {
    ...REMAINING_GRID,
    retotal: writes.totals,
    columns: REMAINING_GRID.columns.map((column) => entered(column, writes)),
  };
}
