// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the three grids of a structure — the planning, the estimate, the remaining to commit — add
 * to their columns when they read a comparison to a base (WF-IHM-0150, US-2340): the base each
 * cell that differs carries (`GridColumn.base`, the value the server says the base had, marked by
 * `BaseMark`), and the columns of difference — of each date in calendar days, of each duration in
 * working time, of each amount —, hidden until chosen and offered only while a comparison is read
 * (`GridConfig.comparing`). A cell is marked when `base` of its node holds its field, a column of
 * difference reads `deltas`: the grid compares nothing and computes nothing (WF-ARC-0020). A
 * comparison changes no column that is shown.
 *
 * The columns of difference are in the configuration whether a comparison is read or not, so that
 * the account keeps their settings with those of the grid, whatever the address it reads.
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { useCurrency } from "@/currency/context";
import { formatDecimal, formatPlanningDate, formatShare } from "@/i18n/format";

import {
  formatCell,
  type CellFormat,
  type ColumnLabel,
  type GridColumn,
  type GridConfig,
} from "./columns";
import { type GridNode, nodeDifference } from "./nodes";
import { PredecessorLinks } from "./planning-cells";

/** A duration, in the unit of its entry (WF-PLA-0160). */
type Duration = components["schemas"]["Duration"];
type WorkInstant = components["schemas"]["WorkInstant"];
type Computable = components["schemas"]["Computable"];
type SchedulingMode = components["schemas"]["SchedulingMode"];
type TaskProgress = components["schemas"]["TaskProgress"];
type Predecessor = components["schemas"]["Predecessor"];

/**
 * The facets of the base of a node and of its differences, as the contract gives them
 * (`ComparedNodeRead.base`, `deltas`): a column reads its field by a key of these types, and its
 * value by the type the contract gives it, down to the access for the base — a field renamed or
 * retyped in the contract is a failure of the type, never a cell left without its mark, unsaid
 * (#3781). The differences (`deltas`) are typed to the facet alone: `DeltaCell` still reads a
 * `value: unknown` (#3795).
 */
type TaskBase = components["schemas"]["ComparedTaskFacet"];
type LineBase = components["schemas"]["ComparedEstimateLineFacet"];
type TaskDeltas = components["schemas"]["TaskDeltas"];
type LineDeltas = components["schemas"]["EstimateLineDeltas"];

/** The fields of a facet whose value, when it has one, is of a type. */
export type FieldsOf<Facet, Value> = {
  [Key in keyof Facet]-?: NonNullable<Facet[Key]> extends Value ? Key : never;
}[keyof Facet];

/** A value shown by the format of its column: a text, a decimal, an amount, a date. */
type Plain = string | number;

/**
 * The field of a node a column shows, in the base of a task and of a line, and how it is shown: the
 * field a key whose value has the type its showing reads.
 */
type BaseField =
  | {
      readonly shown: "plain";
      readonly task?: FieldsOf<TaskBase, Plain>;
      readonly line?: FieldsOf<LineBase, Plain>;
    }
  | { readonly shown: "instant"; readonly task: FieldsOf<TaskBase, WorkInstant> }
  | { readonly shown: "duration"; readonly task: FieldsOf<TaskBase, Duration> }
  | { readonly shown: "share"; readonly task: FieldsOf<TaskBase, Computable> }
  | { readonly shown: "mode"; readonly task: FieldsOf<TaskBase, SchedulingMode> }
  | { readonly shown: "progress"; readonly task: FieldsOf<TaskBase, TaskProgress> }
  | { readonly shown: "predecessors" };

/** The fields that a column of the grids shows, by the key of the column. */
const BASE_FIELDS: Readonly<Record<string, BaseField>> = {
  label: { shown: "plain", task: "label", line: "label" },
  description: { shown: "plain", task: "description" },
  scheduling_mode: { shown: "mode", task: "scheduling_mode" },
  duration: { shown: "duration", task: "duration" },
  start: { shown: "instant", task: "start" },
  finish: { shown: "instant", task: "finish" },
  progress: { shown: "progress", task: "progress" },
  physical_progress: { shown: "share", task: "physical_progress" },
  total_float: { shown: "duration", task: "total_float" },
  started_on: { shown: "plain", task: "started_on" },
  completed_on: { shown: "plain", task: "completed_on" },
  predecessors: { shown: "predecessors" },
  work_breakdown: { shown: "plain", task: "work_breakdown_label" },
  cost_category: { shown: "plain", line: "cost_category_label" },
  resource_role: { shown: "plain", line: "resource_role_label" },
  quantity: { shown: "plain", line: "quantity" },
  hours: { shown: "plain", line: "hours" },
  unit_disbursement: { shown: "plain", line: "unit_disbursement" },
  subproject: { shown: "plain", line: "subproject_label" },
  payment_delay_days: { shown: "plain", line: "payment_delay_days" },
  base_amount: { shown: "plain", task: "base_amount", line: "base_amount" },
  budgeted_amount: { shown: "plain", task: "budgeted_amount", line: "budgeted_amount" },
  reestimated_amount: { shown: "plain", task: "reestimated_amount", line: "reestimated_amount" },
  previous_quantity: { shown: "plain", line: "previous_quantity" },
  previous_hours: { shown: "plain", line: "previous_hours" },
  previous_unit_disbursement: { shown: "plain", line: "previous_unit_disbursement" },
  previous_reestimated_amount: { shown: "plain", line: "previous_reestimated_amount" },
};

/** What a difference is: a number of calendar days, a duration, an amount. */
type DeltaKind = "days" | "duration" | "money";

/** The fields that have a difference: the keys of the differences of a task or of a line. */
type DeltaField = keyof TaskDeltas | keyof LineDeltas;

/** A column of difference: the field it is the difference of, its label, what the difference is. */
interface Delta {
  readonly field: DeltaField;
  readonly label: ColumnLabel;
  readonly kind: DeltaKind;
}

/** The columns of difference, by the field they are the difference of. */
const DELTAS: readonly Delta[] = [
  { field: "start", label: "deltaStartDate", kind: "days" },
  { field: "finish", label: "deltaFinishDate", kind: "days" },
  { field: "started_on", label: "deltaStartedOn", kind: "days" },
  { field: "completed_on", label: "deltaCompletedOn", kind: "days" },
  { field: "duration", label: "deltaDuration", kind: "duration" },
  { field: "total_float", label: "deltaTotalFloat", kind: "duration" },
  { field: "unit_disbursement", label: "deltaUnitDisbursement", kind: "money" },
  { field: "base_amount", label: "deltaReferenceAmount", kind: "money" },
  { field: "budgeted_amount", label: "deltaBudgetedAmount", kind: "money" },
  { field: "reestimated_amount", label: "deltaReestimatedAmount", kind: "money" },
  { field: "previous_unit_disbursement", label: "deltaPreviousUnitDisbursement", kind: "money" },
  { field: "previous_reestimated_amount", label: "deltaPreviousReestimatedAmount", kind: "money" },
];

/** Whether a value is a duration: a quantity in a unit. */
function isDuration(value: unknown): value is Duration {
  if (typeof value !== "object" || value === null) {
    return false;
  }
  const { value: quantity, unit } = value as Partial<Record<keyof Duration, unknown>>;
  return typeof quantity === "string" && typeof unit === "string";
}

/**
 * What the base of a node carried of a field, typed as the contract types it, and how it is shown;
 * `empty` for a base that held no value of it — never for one it holds malformed, which its showing
 * fails on rather than say nothing (#3781).
 */
type BaseHeld =
  | { readonly shown: "empty" }
  | { readonly shown: "plain"; readonly value: Plain }
  | { readonly shown: "instant"; readonly value: WorkInstant }
  | { readonly shown: "duration"; readonly value: Duration }
  | { readonly shown: "share"; readonly value: Computable }
  | { readonly shown: "mode"; readonly value: SchedulingMode }
  | { readonly shown: "progress"; readonly value: TaskProgress }
  | { readonly shown: "predecessors"; readonly value: readonly Predecessor[] };

/** What a base held of a field, if it holds the field: its value, as the contract types it. */
function carried<Facet extends object, Key extends keyof Facet>(
  facet: Facet | undefined,
  field: Key | undefined,
): { readonly value: Facet[Key] } | undefined {
  return facet === undefined || field === undefined || !Object.hasOwn(facet, field)
    ? undefined
    : { value: facet[field] };
}

/** A base that held no value of a field. */
const EMPTY: BaseHeld = { shown: "empty" };

/** What a base held of a field it holds, empty when it held no value. */
function filled<Value>(
  held: { readonly value: Value | null | undefined } | undefined,
  shown: (value: Value) => BaseHeld,
): BaseHeld | undefined {
  if (held === undefined) {
    return undefined;
  }
  const { value } = held;
  return value === null || value === undefined || value === "" ? EMPTY : shown(value);
}

/**
 * What the base of a node held of the field of a column; none when it does not hold the field: the
 * cell does not differ.
 */
function heldOf(spec: BaseField, row: GridNode): BaseHeld | undefined {
  const { base } = row;
  if (base === null || base === undefined) {
    return undefined;
  }
  const task = row.kind === "task" ? base.task : undefined;
  const line = row.kind === "task" ? undefined : base.estimate_line;
  switch (spec.shown) {
    case "predecessors":
      return filled(carried(base, "predecessors"), (value) => ({ shown: spec.shown, value }));
    case "plain":
      return filled(carried(task, spec.task) ?? carried(line, spec.line), (value) => ({
        shown: spec.shown,
        value,
      }));
    case "instant":
      return filled(carried(task, spec.task), (value) => ({ shown: spec.shown, value }));
    case "duration":
      return filled(carried(task, spec.task), (value) => ({ shown: spec.shown, value }));
    case "share":
      return filled(carried(task, spec.task), (value) => ({ shown: spec.shown, value }));
    case "mode":
      return filled(carried(task, spec.task), (value) => ({ shown: spec.shown, value }));
    case "progress":
      return filled(carried(task, spec.task), (value) => ({ shown: spec.shown, value }));
  }
}

/**
 * The value the base of a cell carried, as the cell would have shown it. A value is read as the
 * contract types it: one malformed fails here — a date that is no date, a decimal that is none, a
 * share without its `is_computable`, a mode or a progress the catalogue does not name, a text that
 * is an object —, never shown as a base that held nothing (#3781).
 */
function BaseValue({ held, format }: { readonly held: BaseHeld; readonly format: CellFormat }) {
  const t = useTranslations();
  const locale = useLocale();
  const currency = useCurrency();
  switch (held.shown) {
    case "empty":
      return t("grid.compared.empty");
    case "instant":
      return formatPlanningDate(held.value.date, locale, "short");
    case "duration":
      return t("planningGrid.duration", {
        value: formatDecimal(held.value.value, locale),
        unit: named(t, "enums.DurationUnit", held.value.unit),
      });
    case "share":
      return isComputable(held.value)
        ? formatShare(computedShare(held.value), locale, (key, values) => t(`share.${key}`, values))
        : t("indicator.notComputable");
    case "mode":
      return named(t, "enums.SchedulingMode", held.value);
    case "progress":
      return named(t, "enums.TaskProgress", held.value);
    case "predecessors":
      return <PredecessorLinks links={held.value} />;
    case "plain":
      return formatCell(format, plainText(held.value), locale, currency);
  }
}

/** The name of an enumerated value of the base, which the catalogue must know: else it fails. */
function named(t: ReturnType<typeof useTranslations>, scope: string, value: unknown): string {
  // The key is built from a value the contract types but the base may not hold: the catalogue is
  // asked by its loose form, which is the point.
  const loose = t as unknown as { (key: string): string; has(key: string): boolean };
  if (typeof value !== "string" || !loose.has(`${scope}.${value}`)) {
    throw new RangeError(`Not a value of ${scope}: ${JSON.stringify(value)}`);
  }
  return loose(`${scope}.${value}`);
}

/** Whether a share is computable, as the contract says it: a boolean, else it fails. */
function isComputable({ is_computable: computable }: Computable): boolean {
  if (typeof computable !== "boolean") {
    throw new RangeError(`A share without \`is_computable\`: ${JSON.stringify(computable)}`);
  }
  return computable;
}

/** The text of a value shown as it is: a string or a number, else it fails. */
function plainText(value: Plain): string {
  if (typeof value !== "string" && typeof value !== "number") {
    throw new RangeError(`Not a text nor a number: ${JSON.stringify(value)}`);
  }
  return String(value);
}

/**
 * The value of a share the server says computable, which the contract then gives. A `Computable`
 * computable with a null value fails — an API defect, the contract saying « null when not
 * computable » —, rather than read « not computable »: the choice is to say the defect, not hide it.
 */
function computedShare({ value }: Computable): string {
  if (value === null) {
    throw new RangeError("A share said computable carries no value");
  }
  return value;
}

/**
 * What the base of a node carried of the field of a column, as the column would show it; none when
 * the base does not hold the field: the cell does not differ.
 */
function baseOf(spec: BaseField, format: CellFormat): (row: GridNode) => ReactNode {
  return function baseOfRow(row) {
    const held = heldOf(spec, row);
    return held === undefined ? undefined : <BaseValue held={held} format={format} />;
  };
}

/** The difference of a field of a node, when its base differs and holds a value for it. */
function deltaOf(row: GridNode, field: DeltaField): unknown {
  const facet: Partial<Record<DeltaField, unknown>> | undefined =
    row.kind === "task" ? row.deltas?.task : row.deltas?.estimate_line;
  return facet?.[field];
}

/** An exact decimal that reads as zero: `0`, `-0`, `0.00`. */
const ZERO = /^-?0+(\.0+)?$/;

/** A difference, its sign written in front of a positive one: the number of days, the amount. */
function signed(raw: string, text: string): string {
  return raw.startsWith("-") || ZERO.test(raw) ? text : `+${text}`;
}

/** The cell of a difference: a number of days, a duration in its unit, an amount; blank for none. */
function DeltaCell({ kind, value }: { readonly kind: DeltaKind; readonly value: unknown }) {
  const t = useTranslations();
  const locale = useLocale();
  const currency = useCurrency();
  if (value === null || value === undefined) {
    return null;
  }
  switch (kind) {
    case "days": {
      if (typeof value !== "number") {
        return null;
      }
      const days = String(value);
      return t("grid.compared.days", { days: signed(days, formatDecimal(days, locale)) });
    }
    case "duration":
      return isDuration(value)
        ? t("planningGrid.duration", {
            value: signed(value.value, formatDecimal(value.value, locale)),
            unit: t(`enums.DurationUnit.${value.unit}`),
          })
        : null;
    case "money":
      return typeof value === "string"
        ? signed(value, formatCell("money", value, locale, currency))
        : null;
  }
}

/**
 * The column of the difference to the base of a column: hidden until chosen, shown while a comparison
 * is read, the difference as the server gives it (`deltas`) and nothing where there is none.
 */
function deltaColumn<Row extends GridNode, Sort extends string, Totals>(
  source: GridColumn<Row, Sort, Totals>,
  delta: Delta,
): GridColumn<Row, Sort, Totals> {
  const raw = (row: Row) => deltaOf(row, delta.field) ?? undefined;
  return {
    key: `delta_${source.key}`,
    label: delta.label,
    format: delta.kind === "money" ? "money" : "decimal",
    width: Math.max(source.width, 96),
    hidden: true,
    compared: true,
    sorts: false,
    // Never sorted nor shown as it is: the cell renders the difference.
    value: () => undefined,
    render: (row) => <DeltaCell kind={delta.kind} value={raw(row)} />,
  };
}

/**
 * A grid of a structure with what a comparison adds: its rows marked by the difference the server
 * says each bears, its cells that differ marked with the value of the base, its columns of
 * difference. `comparing` says whether it reads one.
 */
export function comparedGrid<Row extends GridNode, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  comparing: boolean,
): GridConfig<Row, Sort, Totals> {
  const columns = config.columns.flatMap((column) => {
    const spec = BASE_FIELDS[column.key];
    const marked = spec === undefined ? column : { ...column, base: baseOf(spec, column.format) };
    const delta = DELTAS.find((each) => each.field === column.key);
    return delta === undefined ? [marked] : [marked, deltaColumn(column, delta)];
  });
  return {
    ...config,
    columns,
    comparing,
    ...(comparing ? { difference: nodeDifference } : {}),
  };
}

/**
 * A grid of a structure, with the column of the marks of a difference where the structure read is a
 * differential or the grid reads a comparison (`GridConfig.difference`), and the marks and the
 * columns of a comparison (`comparedGrid`), offered while it reads one (`comparing`).
 */
export function withDifference<Row extends GridNode, Sort extends string, Totals>(
  config: GridConfig<Row, Sort, Totals>,
  differential: boolean | undefined,
  comparing = false,
): GridConfig<Row, Sort, Totals> {
  const marked = differential === true ? { ...config, difference: nodeDifference } : config;
  return comparedGrid(marked, comparing);
}
