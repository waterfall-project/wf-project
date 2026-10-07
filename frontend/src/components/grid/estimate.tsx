// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the estimate (WF-DEV-0050): the common tree of a structure
 * (`listNodes`), its tasks and the lines they bear, each row numbered and marked by the icon of
 * its nature; the label, the quantity, the effort, the unit disbursement, and the two amounts the
 * server computes and never lets anyone enter, of a line as of a task, summary included — the
 * amount at the year of reference (`base_amount`, WF-DEV-0030) and the amount corrected for
 * inflation, projected on the year of consumption (WF-DEV-0040) —, never the budgeted nor the
 * re-estimated amount (#235). The figures of a provision are computed too, from its risk, which
 * its node says (`computed_fields`, WF-IHM-0030). The totals are those of the answer: the hours
 * and the two amounts of the lines retained, never the amounts of the tasks, which would count
 * them twice.
 *
 * Each column sorts by the column of the contract of the same name. The category, the role and
 * the sub-project of a line are named by the labels the server resolves, the object active or
 * deactivated (#305) — never by bringing the lists of the reference data together here
 * (WF-ARC-0020). A line that employs a deactivated object of the reference data says so
 * (`uses_inactive_object`), and the grid marks it by a mark of its own, named — no zone of the
 * scale of signals, which the server alone gives —, without deducing anything from the lists
 * (WF-REF-0010, #349); the payment delay and the sub-project are shown with it (WF-DEV-0050).
 *
 * A line is entered whole from the keyboard (WF-IHM-0040): its label, its category, its role and
 * its sub-project, chosen from their lists, its quantity, its effort, its unit disbursement and
 * its payment delay, each written alone by `updateEstimateLine`, where the node names the field
 * among those it accepts (`editable_fields`, #219) and not among those it computes — a line of
 * labour takes no unit disbursement nor payment delay, another no role nor effort, a provision
 * none of them (WF-DEV-0020), which the grid never deduces from the nature of the category —; the
 * label of a task by `updateTaskFacet` (`estimateGrid`).
 */
import { ToggleLeft } from "lucide-react";

import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";

import {
  type CellValue,
  type Choice,
  type EntryKind,
  type GridColumn,
  type GridConfig,
  type GridPaste,
  type RowsWritten,
  sortColumns,
} from "./columns";
import { computedAmount, computedWhereNamed } from "./computed-nodes";
import { InactiveObjectCell } from "./estimate-cells";
import {
  type AnyNodeFields,
  type GridNode,
  LABEL_COLUMN,
  NODE_TREE,
  nodeKey,
  nodeNumber,
  type NodeSortColumn,
  type NodeRows,
  type NodeTotals,
  type RowOf,
} from "./nodes";

/**
 * What the columns of the estimate read of a node, beyond what every grid reads: the amounts of a
 * task, the figures of a line, its amounts, the labels of its category, its role and its
 * sub-project, the identifiers of its category and its sub-project, which an entry starts from,
 * its payment delay, and whether it employs a deactivated object. The page asks for these alone
 * (`fields`) and hands the grid these alone (`projectNodes`).
 */
export const ESTIMATE_FIELDS = {
  node: [],
  task: ["base_amount", "inflated_amount"],
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
    "inflated_amount",
  ],
} as const satisfies AnyNodeFields;

/** A node as the grid of the estimate reads it. */
export type EstimateNode = RowOf<typeof ESTIMATE_FIELDS>;

/** The grid of the estimate. */
export const ESTIMATE_GRID: GridConfig<EstimateNode, NodeSortColumn, NodeTotals> = {
  key: "estimate",
  searched: true,
  name: "estimate",
  rowKey: nodeKey,
  rowNumber: nodeNumber,
  tree: NODE_TREE,
  columns: [
    LABEL_COLUMN,
    // A category and a role are named by the label the server resolves; an entry starts from
    // their identifier (`estimateGrid`).
    {
      key: "cost_category",
      label: "category",
      format: "text",
      width: 160,
      sortBy: "cost_category",
      value: (node) => node.estimate_line?.cost_category_label,
    },
    {
      key: "resource_role",
      label: "role",
      format: "text",
      width: 160,
      sortBy: "resource_role",
      value: (node) => node.estimate_line?.resource_role_label,
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
    // The sub-project is named by the label the server resolves (#349); the payment delay is a
    // whole number of days, which the cumulative cost curve shifts the line by (WF-IND-0100).
    {
      key: "subproject",
      label: "subproject",
      format: "text",
      width: 160,
      sortBy: "subproject",
      value: (node) => node.estimate_line?.subproject_label ?? null,
    },
    {
      key: "payment_delay_days",
      label: "paymentDelay",
      format: "decimal",
      width: 88,
      sortBy: "payment_delay_days",
      value: (node) => paymentDelay(node),
    },
    // A line that employs a deactivated object of the reference data, which the server says
    // (WF-REF-0010): a mark of its own, a narrow column headed by the same icon; the server sorts
    // by no such column, and the column offers no value to sort by.
    {
      key: "inactive_object",
      label: "inactiveObject",
      format: "text",
      align: "center",
      width: 44,
      icon: ToggleLeft,
      value: () => undefined,
      render: (node) => <InactiveObjectCell node={node} />,
    },
    // The two amounts of WF-DEV-0050, of a line, of a task — the sum of its subtree — and of
    // the totals, as the server gives them.
    {
      key: "base_amount",
      label: "referenceAmount",
      format: "money",
      width: 128,
      computed: computedAmount("base_amount"),
      sortBy: "base_amount",
      value: (node) => node.task?.base_amount ?? node.estimate_line?.base_amount,
      total: (totals) => totals.base_amount,
    },
    {
      key: "inflated_amount",
      label: "inflatedAmount",
      format: "money",
      width: 128,
      computed: computedAmount("inflated_amount"),
      sortBy: "inflated_amount",
      value: (node) => node.task?.inflated_amount ?? node.estimate_line?.inflated_amount,
      total: (totals) => totals.inflated_amount,
    },
  ],
};

/**
 * The payment delay of a line, as the exact text of the whole number of days the contract gives;
 * none for a task, or a line without one — left out by the projection or null alike.
 */
function paymentDelay(node: EstimateNode): CellValue {
  const days = node.estimate_line?.payment_delay_days;
  return days === undefined || days === null ? null : String(days);
}

/**
 * The rows of a grid that takes no entry of a sub-project — a revision not open to entry, or a
 * list of the sub-projects the API refused —: without the identifier of the sub-project of a line,
 * which only an entry starts from, the label shown as it is.
 */
export function withoutSubprojectIds(rows: NodeRows<EstimateNode>): NodeRows<EstimateNode> {
  return {
    ...rows,
    items: rows.items.map((node) => {
      const line = node.estimate_line;
      if (line?.subproject_id === undefined) {
        return node;
      }
      const shown = { ...line };
      delete shown.subproject_id;
      return { ...node, estimate_line: shown };
    }),
  };
}

/** The columns of the contract the grid of the estimate sorts by. */
export const ESTIMATE_SORT_COLUMNS = sortColumns(ESTIMATE_GRID);

/** What a write of the grid of the estimate answers, as the grid reads it. */
export type EstimateWritten = RowsWritten<EstimateNode, NodeTotals>;

/** The fields of a line of the estimate an entry writes: the cell entered, nothing else (#178). */
export type LineChange = Partial<
  Pick<
    components["schemas"]["EstimateLineUpdate"],
    | "label"
    | "cost_category_id"
    | "resource_role_id"
    | "quantity"
    | "hours"
    | "unit_disbursement"
    | "payment_delay_days"
    | "subproject_id"
  >
>;

/**
 * How the grid of the estimate writes a cell: a field of a line, the label of a task — the row
 * answered as the grid reads it. The label of a task is the planning's (`updateTaskFacet`): none,
 * and a task's label is not entered here. A block pasted from a spreadsheet is written in two
 * steps, by the structure (`previewPaste`, `applyPaste`, WF-IHM-0050).
 */
export interface EstimateWrites {
  readonly line: (node: EstimateNode, change: LineChange) => Promise<Outcome<EstimateWritten>>;
  readonly task?:
    ((node: EstimateNode, label: string) => Promise<Outcome<EstimateWritten>>) | undefined;
  readonly paste: GridPaste<EstimateNode, NodeSortColumn, NodeTotals>;
  /** Read anew the totals of a reading the writes do not answer them for; none, they do. */
  readonly totals?: (() => Promise<Outcome<NodeTotals>>) | undefined;
}

/**
 * The reference data the grid offers the categories and the roles of the lines from, and the
 * sub-projects of the project, each by its code and its label; a list the API refused is none —
 * its column is not entered, and still named by the server.
 */
export interface EstimateReference {
  readonly categories: readonly Choice[] | undefined;
  readonly roles: readonly Choice[] | undefined;
  readonly subprojects: readonly Choice[] | undefined;
}

/** A field of a facet a node may accept, as the contract names it. */
type EditableField = components["schemas"]["EditableField"];

/**
 * How a column of a line is entered: what it takes, the field the node must accept for it, what
 * it writes, what it starts from.
 */
interface Entered {
  readonly kind: EntryKind;
  readonly field: (node: GridNode) => EditableField;
  readonly change: (value: string | null) => LineChange;
  /** The value of the contract an entry starts from; by default, what the column shows. */
  readonly read?: (node: EstimateNode) => CellValue;
}

/**
 * How a list of the reference data is entered: its choices, the field it writes, the value it
 * starts from — a cell whose identifier the list does not know is not entered, so that no first
 * choice is written for it unseen.
 */
function listEntered(
  choices: readonly Choice[],
  field: EditableField,
  nullable: boolean,
  read: (node: EstimateNode) => CellValue,
  change: (value: string | null) => LineChange,
): Entered & { readonly known: (node: EstimateNode) => boolean } {
  const ids = new Set(choices.map((choice) => choice.id));
  return {
    kind: { type: "choice", choices: () => choices, nullable },
    field: () => field,
    change,
    read,
    known: (node) => {
      const id = read(node);
      return id === null || id === undefined || ids.has(id);
    },
  };
}

/**
 * The columns of a line that take an entry, the lists of a category, a role and a sub-project
 * among them.
 */
function enteredColumns(
  reference: EstimateReference,
): Readonly<Record<string, Entered & { readonly known?: (node: EstimateNode) => boolean }>> {
  const { categories, roles, subprojects } = reference;
  return {
    // The contract takes a label of 1 to 300 characters: a task's, or a line's.
    label: {
      kind: { type: "text", maxLength: 300 },
      field: (node) => (bearsLine(node) ? "estimate_line.label" : "task.label"),
      change: (value) => ({ label: value ?? "" }),
    },
    ...(categories === undefined
      ? {}
      : {
          cost_category: listEntered(
            categories,
            "estimate_line.cost_category_id",
            false,
            (node) => node.estimate_line?.cost_category_id,
            (value) => (value === null ? {} : { cost_category_id: value }),
          ),
        }),
    ...(roles === undefined
      ? {}
      : {
          resource_role: listEntered(
            roles,
            "estimate_line.resource_role_id",
            true,
            (node) => node.estimate_line?.resource_role_id,
            (value) => ({ resource_role_id: value }),
          ),
        }),
    quantity: {
      kind: { type: "decimal", nullable: false },
      field: () => "estimate_line.quantity",
      change: (value) => (value === null ? {} : { quantity: value }),
    },
    hours: {
      kind: { type: "decimal", nullable: true },
      field: () => "estimate_line.hours",
      change: (value) => ({ hours: value }),
    },
    unit_disbursement: {
      kind: { type: "money", nullable: true },
      field: () => "estimate_line.unit_disbursement",
      change: (value) => ({ unit_disbursement: value }),
    },
    ...(subprojects === undefined
      ? {}
      : {
          subproject: listEntered(
            subprojects,
            "estimate_line.subproject_id",
            true,
            (node) => node.estimate_line?.subproject_id ?? null,
            (value) => ({ subproject_id: value }),
          ),
        }),
    // A whole number of days, which the entry validates as such: the contract takes an integer.
    payment_delay_days: {
      kind: { type: "integer", nullable: true },
      field: () => "estimate_line.payment_delay_days",
      change: (value) => ({ payment_delay_days: value === null ? null : Number(value) }),
    },
  };
}

/** Whether a node bears a line of the estimate. */
function bearsLine(node: GridNode): boolean {
  return node.estimate_line !== undefined && node.estimate_line !== null;
}

/**
 * Whether the cell of a column takes an entry in a row: the node accepts the field it writes —
 * which the node says, never the grid by the nature of its category (#219) —, and, for the label
 * of a task, the planning may be entered.
 */
function takes(label: boolean, writes: EstimateWrites, spec: Entered, node: EstimateNode): boolean {
  const accepted = node.editable_fields.includes(spec.field(node));
  return accepted && (label && !bearsLine(node) ? writes.task !== undefined : bearsLine(node));
}

/** A column of the estimate, entered through `writes`: the fields of a line, and a task's label. */
function entered(
  column: GridColumn<EstimateNode, NodeSortColumn, NodeTotals>,
  spec: (Entered & { readonly known?: (node: EstimateNode) => boolean }) | undefined,
  writes: EstimateWrites | undefined,
): GridColumn<EstimateNode, NodeSortColumn, NodeTotals> {
  if (spec === undefined || writes === undefined) {
    return column;
  }
  const label = column.key === "label";
  return {
    ...column,
    entry: {
      kind: spec.kind,
      in: (node) =>
        takes(label, writes, spec, node) &&
        column.computed?.in(node) !== true &&
        spec.known?.(node) !== false,
      value: spec.read ?? column.value,
      write: (node, value) => {
        const task = label && !bearsLine(node) ? writes.task : undefined;
        return task === undefined ? writes.line(node, spec.change(value)) : task(node, value ?? "");
      },
    },
  };
}

/**
 * The grid of the estimate: its cells entered and a block pasted through `writes`; none, and the
 * grid is read only, taking neither entry nor paste. A line takes its label, category, role,
 * quantity, effort, unit disbursement, sub-project and payment delay, where its node accepts the
 * field and the server does not compute it — a category, a role or a sub-project from the lists
 * of the reference data, which must know the one the line bears, a deactivated one included —; a
 * task, its label, where its node accepts it and the planning is entered.
 */
export function estimateGrid(
  reference: EstimateReference,
  writes?: EstimateWrites,
): GridConfig<EstimateNode, NodeSortColumn, NodeTotals> {
  const specs = enteredColumns(reference);
  return {
    ...ESTIMATE_GRID,
    paste: writes?.paste,
    retotal: writes?.totals,
    columns: ESTIMATE_GRID.columns.map((column) => entered(column, specs[column.key], writes)),
  };
}
