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
import { signed } from "./signed";

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
 * value by the type the contract gives it, down to the access — for the base as for the differences
 * (`deltas`): a field renamed or retyped in the contract is a failure of the type, never a cell left
 * without its mark, unsaid (#3781, #3795).
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

type Money = components["schemas"]["Money"];

/**
 * What a difference is, and the field of the differences of a task, of a line, that holds it, a key
 * whose value has the type the difference is read as: a number of calendar days, a duration, an
 * amount.
 */
type DeltaField =
  | { readonly kind: "days"; readonly task: FieldsOf<TaskDeltas, number> }
  | { readonly kind: "duration"; readonly task: FieldsOf<TaskDeltas, Duration> }
  | {
      readonly kind: "money";
      readonly task?: FieldsOf<TaskDeltas, Money>;
      readonly line?: FieldsOf<LineDeltas, Money>;
    };

/** A column of difference: the key of the column it is the difference of, its label, its field. */
type Delta = DeltaField & { readonly column: string; readonly label: ColumnLabel };

/** The columns of difference, by the column they are the difference of. */
const DELTAS: readonly Delta[] = [
  { column: "start", label: "deltaStartDate", kind: "days", task: "start" },
  { column: "finish", label: "deltaFinishDate", kind: "days", task: "finish" },
  { column: "started_on", label: "deltaStartedOn", kind: "days", task: "started_on" },
  { column: "completed_on", label: "deltaCompletedOn", kind: "days", task: "completed_on" },
  { column: "duration", label: "deltaDuration", kind: "duration", task: "duration" },
  { column: "total_float", label: "deltaTotalFloat", kind: "duration", task: "total_float" },
  {
    column: "unit_disbursement",
    label: "deltaUnitDisbursement",
    kind: "money",
    line: "unit_disbursement",
  },
  {
    column: "base_amount",
    label: "deltaReferenceAmount",
    kind: "money",
    task: "base_amount",
    line: "base_amount",
  },
  {
    column: "budgeted_amount",
    label: "deltaBudgetedAmount",
    kind: "money",
    task: "budgeted_amount",
    line: "budgeted_amount",
  },
  {
    column: "reestimated_amount",
    label: "deltaReestimatedAmount",
    kind: "money",
    task: "reestimated_amount",
    line: "reestimated_amount",
  },
  {
    column: "previous_unit_disbursement",
    label: "deltaPreviousUnitDisbursement",
    kind: "money",
    line: "previous_unit_disbursement",
  },
  {
    column: "previous_reestimated_amount",
    label: "deltaPreviousReestimatedAmount",
    kind: "money",
    line: "previous_reestimated_amount",
  },
];

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
        unit: named(t, "enums.DurationUnit", held.value.unit, DURATION_UNITS),
      });
    case "share":
      return isComputable(held.value)
        ? formatShare(computedShare(held.value), locale, (key, values) => t(`share.${key}`, values))
        : t("indicator.notComputable");
    case "mode":
      return named(t, "enums.SchedulingMode", held.value, SCHEDULING_MODES);
    case "progress":
      return named(t, "enums.TaskProgress", held.value, TASK_PROGRESS);
    case "predecessors":
      return <PredecessorLinks links={held.value} />;
    case "plain":
      return formatCell(format, plainText(held.value), locale, currency);
  }
}

/** The translator the grid reads its labels with. */
type Translator = ReturnType<typeof useTranslations>;

/**
 * The values of the enumerations of the contract a base or a difference names, each with its place
 * in the catalogue: one added to the contract is a failure of the type until it is here. The
 * catalogue alone cannot tell them from the keys of the prototype of an object (`constructor`,
 * `__proto__`), which its `has` answers for (#3798).
 */
const SCHEDULING_MODES: Readonly<Record<SchedulingMode, true>> = { automatic: true, manual: true };
const TASK_PROGRESS: Readonly<Record<TaskProgress, true>> = {
  not_started: true,
  started: true,
  completed: true,
};
const DURATION_UNITS: Readonly<Record<Duration["unit"], true>> = {
  min: true,
  h: true,
  d: true,
  w: true,
  mo: true,
  emin: true,
  eh: true,
  ed: true,
  ew: true,
  emo: true,
};

/**
 * The name of an enumerated value of the base, which the contract lists (`known`) and the catalogue
 * must know: else it fails.
 */
function named(
  t: Translator,
  scope: string,
  value: unknown,
  known: Readonly<Record<string, true>>,
): string {
  // The key is built from a value the contract types but the base may not hold: only `has` is asked
  // by a free key, which is the point, and the key it has just found in the catalogue is the one
  // `t` reads — the typed union of every key of the catalogue is too large to build from a string.
  const catalogue = t as unknown as { has(key: string): boolean };
  const key = `${scope}.${String(value)}`;
  if (typeof value !== "string" || !Object.hasOwn(known, value) || !catalogue.has(key)) {
    throw new RangeError(`Not a value of ${scope}: ${JSON.stringify(value)}`);
  }
  return t(key as never);
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

/** What the differences of a node held of a field, as the contract types it, and how it is shown. */
type DeltaHeld =
  | { readonly kind: "days"; readonly value: number }
  | { readonly kind: "duration"; readonly value: Duration }
  | { readonly kind: "money"; readonly value: Money };

/** What the differences of a task held of a field, as the contract types it. */
function taskDelta<Key extends keyof TaskDeltas>(
  row: GridNode,
  field: Key,
): TaskDeltas[Key] | undefined {
  return row.kind === "task" ? row.deltas?.task?.[field] : undefined;
}

/** What the differences of a node held of an amount: of its task, or of its line. */
function moneyDelta(
  row: GridNode,
  delta: Delta & { readonly kind: "money" },
): Money | null | undefined {
  if (row.kind === "task") {
    return delta.task === undefined ? undefined : row.deltas?.task?.[delta.task];
  }
  return delta.line === undefined ? undefined : row.deltas?.estimate_line?.[delta.line];
}

/**
 * The difference of a field of a node, typed as the contract types it, when its base differs and
 * holds a value for it; none otherwise — a field the differences leave out or hold `null`.
 */
function deltaOf(row: GridNode, delta: Delta): DeltaHeld | undefined {
  switch (delta.kind) {
    case "days": {
      const value = taskDelta(row, delta.task);
      return value === null || value === undefined ? undefined : { kind: delta.kind, value };
    }
    case "duration": {
      const value = taskDelta(row, delta.task);
      return value === null || value === undefined ? undefined : { kind: delta.kind, value };
    }
    case "money": {
      const value = moneyDelta(row, delta);
      return value === null || value === undefined ? undefined : { kind: delta.kind, value };
    }
  }
}

/**
 * The cell of a difference: a number of days, a duration in its unit, an amount; blank for none. A
 * difference is read as the contract types it: one malformed fails here — days that are no number, a
 * duration without its quantity or in a unit the catalogue does not name, an amount that is no text
 * —, never shown as no difference (#3795).
 */
function DeltaCell({ held }: { readonly held: DeltaHeld | undefined }) {
  const t = useTranslations();
  const locale = useLocale();
  const currency = useCurrency();
  switch (held?.kind) {
    case undefined:
      return null;
    case "days": {
      if (typeof held.value !== "number") {
        throw new RangeError(`Not a number of days: ${JSON.stringify(held.value)}`);
      }
      const days = String(held.value);
      return t("grid.compared.days", { days: signed(days, formatDecimal(days, locale)) });
    }
    case "duration": {
      const { value, unit } = held.value;
      if (typeof value !== "string") {
        throw new RangeError(`Not a duration: ${JSON.stringify(held.value)}`);
      }
      return t("planningGrid.duration", {
        value: signed(value, formatDecimal(value, locale)),
        unit: named(t, "enums.DurationUnit", unit, DURATION_UNITS),
      });
    }
    case "money":
      if (typeof held.value !== "string") {
        throw new RangeError(`Not an amount: ${JSON.stringify(held.value)}`);
      }
      return signed(held.value, formatCell("money", held.value, locale, currency));
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
    render: (row) => <DeltaCell held={deltaOf(row, delta)} />,
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
    const delta = DELTAS.find((each) => each.column === column.key);
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
