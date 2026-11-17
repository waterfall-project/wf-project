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
import { formatDecimal, formatShare } from "@/i18n/format";

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

/** How the base of a cell is shown, from what the contract gives of the field. */
type Shown = "plain" | "instant" | "duration" | "mode" | "progress" | "share" | "predecessors";

/** The field of a node a column shows, in the base of a task and of a line, and how it is shown. */
interface BaseField {
  readonly task?: string;
  readonly line?: string;
  readonly shown?: Shown;
}

/** The fields that a column of the grids shows, by the key of the column. */
const BASE_FIELDS: Readonly<Record<string, BaseField>> = {
  label: { task: "label", line: "label" },
  description: { task: "description" },
  scheduling_mode: { task: "scheduling_mode", shown: "mode" },
  duration: { task: "duration", shown: "duration" },
  start: { task: "start", shown: "instant" },
  finish: { task: "finish", shown: "instant" },
  progress: { task: "progress", shown: "progress" },
  physical_progress: { task: "physical_progress", shown: "share" },
  total_float: { task: "total_float", shown: "duration" },
  started_on: { task: "started_on" },
  completed_on: { task: "completed_on" },
  predecessors: { shown: "predecessors" },
  work_breakdown: { task: "work_breakdown_label" },
  cost_category: { line: "cost_category_label" },
  resource_role: { line: "resource_role_label" },
  quantity: { line: "quantity" },
  hours: { line: "hours" },
  unit_disbursement: { line: "unit_disbursement" },
  subproject: { line: "subproject_label" },
  payment_delay_days: { line: "payment_delay_days" },
  base_amount: { task: "base_amount", line: "base_amount" },
  budgeted_amount: { task: "budgeted_amount", line: "budgeted_amount" },
  reestimated_amount: { task: "reestimated_amount", line: "reestimated_amount" },
  previous_quantity: { line: "previous_quantity" },
  previous_hours: { line: "previous_hours" },
  previous_unit_disbursement: { line: "previous_unit_disbursement" },
  previous_reestimated_amount: { line: "previous_reestimated_amount" },
};

/** What a difference is: a number of calendar days, a duration, an amount. */
type DeltaKind = "days" | "duration" | "money";

/** The columns of difference, by the key of the column they are the difference of. */
const DELTAS: Readonly<Record<string, { readonly label: ColumnLabel; readonly kind: DeltaKind }>> =
  {
    start: { label: "deltaStartDate", kind: "days" },
    finish: { label: "deltaFinishDate", kind: "days" },
    started_on: { label: "deltaStartedOn", kind: "days" },
    completed_on: { label: "deltaCompletedOn", kind: "days" },
    duration: { label: "deltaDuration", kind: "duration" },
    total_float: { label: "deltaTotalFloat", kind: "duration" },
    unit_disbursement: { label: "deltaUnitDisbursement", kind: "money" },
    base_amount: { label: "deltaReferenceAmount", kind: "money" },
    budgeted_amount: { label: "deltaBudgetedAmount", kind: "money" },
    reestimated_amount: { label: "deltaReestimatedAmount", kind: "money" },
    previous_unit_disbursement: { label: "deltaPreviousUnitDisbursement", kind: "money" },
    previous_reestimated_amount: { label: "deltaPreviousReestimatedAmount", kind: "money" },
  };

/** The value of a field of an object that is read by its name alone. */
type Fields = Readonly<Record<string, unknown>>;

/** The value the base of a cell carried, as the cell would have shown it. */
function BaseValue({
  shown,
  format,
  value,
}: {
  readonly shown: Shown;
  readonly format: CellFormat;
  readonly value: unknown;
}) {
  const t = useTranslations();
  const locale = useLocale();
  const currency = useCurrency();
  if (value === null || value === undefined || value === "") {
    return t("grid.compared.empty");
  }
  switch (shown) {
    case "instant":
      return formatCell("date", (value as { readonly date: string }).date, locale);
    case "duration": {
      const duration = value as Duration;
      return t("planningGrid.duration", {
        value: formatDecimal(duration.value, locale),
        unit: t(`enums.DurationUnit.${duration.unit}`),
      });
    }
    case "mode":
      return t(`enums.SchedulingMode.${value as components["schemas"]["SchedulingMode"]}`);
    case "progress":
      return t(`enums.TaskProgress.${value as components["schemas"]["TaskProgress"]}`);
    case "share": {
      const share = value as components["schemas"]["Computable"];
      return share.is_computable && share.value !== null
        ? formatShare(share.value, locale, (key, values) => t(`share.${key}`, values))
        : t("indicator.notComputable");
    }
    case "predecessors":
      return <PredecessorLinks links={value as readonly components["schemas"]["Predecessor"][]} />;
    case "plain":
      return formatCell(
        format,
        typeof value === "number" ? String(value) : (value as string),
        locale,
        currency,
      );
  }
}

/**
 * What the base of a node carried of the field of a column, as the column would show it; none when
 * the base does not hold the field: the cell does not differ.
 */
function baseOf(spec: BaseField, format: CellFormat): (row: GridNode) => ReactNode {
  const shown = spec.shown ?? "plain";
  return function baseOfRow(row) {
    const { base } = row;
    if (base === null || base === undefined) {
      return undefined;
    }
    if (shown === "predecessors") {
      return Object.hasOwn(base, "predecessors") ? (
        <BaseValue shown={shown} format={format} value={base.predecessors} />
      ) : undefined;
    }
    const facet = row.kind === "task" ? base.task : base.estimate_line;
    const field = row.kind === "task" ? spec.task : spec.line;
    if (facet === undefined || field === undefined || !Object.hasOwn(facet, field)) {
      return undefined;
    }
    return <BaseValue shown={shown} format={format} value={(facet as Fields)[field]} />;
  };
}

/** The difference of a field of a node, when its base differs and holds a value for it. */
function deltaOf(row: GridNode, field: string): unknown {
  const facet = row.kind === "task" ? row.deltas?.task : row.deltas?.estimate_line;
  return facet === undefined ? undefined : (facet as Fields)[field];
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
    case "duration": {
      const duration = value as Duration;
      return t("planningGrid.duration", {
        value: signed(duration.value, formatDecimal(duration.value, locale)),
        unit: t(`enums.DurationUnit.${duration.unit}`),
      });
    }
    case "money": {
      const amount = value as string;
      return signed(amount, formatCell("money", amount, locale, currency));
    }
  }
}

/**
 * The column of the difference to the base of a column: hidden until chosen, shown while a comparison
 * is read, the difference as the server gives it (`deltas`) and nothing where there is none.
 */
function deltaColumn<Row extends GridNode, Sort extends string, Totals>(
  source: GridColumn<Row, Sort, Totals>,
  delta: { readonly label: ColumnLabel; readonly kind: DeltaKind },
): GridColumn<Row, Sort, Totals> {
  const raw = (row: Row) => {
    return deltaOf(row, source.key) ?? undefined;
  };
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
    const delta = DELTAS[column.key];
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
