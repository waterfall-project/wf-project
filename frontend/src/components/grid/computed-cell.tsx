// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A cell of a dense grid whose value the server computes (WF-IHM-0030): shaded by its row, marked
 * by Σ — the one mark of a computed value, which its header bears for a column computed whole —,
 * named « computed » to whoever does not see it, and never entered. Clicked, or pressed from the
 * keyboard, it refuses the entry beside it and names what its value depends on: why the server
 * computes it, and the rows it is drawn from, named as the grid names them — their number, the
 * icon of their nature, their label.
 *
 * The cell is a button, which the pointer and the keyboard reach alike; the entry at the keyboard
 * (US-0120) will open the same refusal from the cell it lands on. Its popover mounts on the first
 * try only: a root of Radix in each computed cell would cost the hydration of the first screen as
 * many contexts, and the second of §4.6.2 counts it.
 */
"use client";

import type { RowData } from "@tanstack/react-table";
import { Sigma } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { type ReactNode, useId, useState } from "react";

import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";

import {
  type ComputedCells,
  type Dependency,
  formatCell,
  type GridColumn,
  type GridConfig,
} from "./columns";

/** A column some of whose cells the server computes. */
export type ComputedColumn<Row, Sort extends string, Totals> = GridColumn<Row, Sort, Totals> & {
  readonly computed: ComputedCells<Row>;
};

/** The cell as a button: the whole of it, the mark at its start and the value at its end. */
const TRIGGER =
  "flex w-full min-w-0 items-center justify-between gap-0.5 rounded-sm text-inherit outline-none focus-visible:ring-[3px] focus-visible:ring-ring";

/** What the refusal of an entry on a computed value reads. */
export interface ComputedRefusalProps<Row, Sort extends string, Totals> {
  readonly config: GridConfig<Row, Sort, Totals>;
  readonly column: GridColumn<Row, Sort, Totals>;
  /** The rows of the answer, among which the dependency names its rows by their indices. */
  readonly rows: readonly Row[];
  readonly dependency: Dependency;
}

/** A row a value depends on, named as the grid names it: its number, its nature, its label. */
function DependencyRow<Row, Sort extends string, Totals>({
  config,
  row,
}: {
  readonly config: GridConfig<Row, Sort, Totals>;
  readonly row: Row;
}) {
  const locale = useLocale();
  const label = config.columns[0];
  return (
    <li className="flex min-w-0 items-center gap-1.5">
      <span className="w-8 shrink-0 text-right text-muted-foreground tabular-nums">
        {config.rowNumber?.(row)}
      </span>
      {config.tree?.nature(row)}
      <span className="truncate">
        {label === undefined ? null : formatCell(label.format, label.value(row), locale)}
      </span>
    </li>
  );
}

/**
 * Render the refusal of an entry on a computed value, in its popover: the value is computed, why,
 * and the rows it depends on. A dialog, named by its title.
 */
export function ComputedRefusal<Row, Sort extends string, Totals>({
  config,
  column,
  rows,
  dependency,
}: ComputedRefusalProps<Row, Sort, Totals>) {
  const t = useTranslations("computedValue");
  const columns = useTranslations("grid.columns");
  const title = useId();
  const listed = useId();
  const named = dependency.rows.flatMap((index) => {
    const row = rows[index];
    return row === undefined ? [] : [row];
  });
  return (
    <PopoverContent aria-labelledby={title} className="w-80 space-y-1.5 text-xs">
      <p id={title} className="flex items-center gap-1.5 text-sm font-medium">
        <Sigma aria-hidden="true" className="size-3.5 shrink-0" />
        {t("title")}
      </p>
      <p>{t("refused", { column: columns(column.label) })}</p>
      {dependency.reasons.map((reason) => (
        <p key={reason} className="text-muted-foreground">
          {t(`reasons.${reason}`)}
        </p>
      ))}
      {named.length === 0 ? null : (
        <>
          <p id={listed} className="font-medium">
            {t("dependsOn")}
          </p>
          <ul
            aria-labelledby={listed}
            tabIndex={0}
            className="max-h-48 space-y-0.5 overflow-y-auto"
          >
            {named.map((row) => (
              <DependencyRow key={config.rowKey(row)} config={config} row={row} />
            ))}
          </ul>
        </>
      )}
    </PopoverContent>
  );
}

/** What a computed cell shows, and where its row stands among the rows of the answer. */
export interface ComputedCellProps<Row, Sort extends string, Totals> {
  readonly config: GridConfig<Row, Sort, Totals>;
  readonly column: ComputedColumn<Row, Sort, Totals>;
  /** The rows of the answer, read once the cell is tried: a function, which a render compares. */
  readonly answer: () => readonly Row[];
  readonly index: number;
  /** The value of the cell, formatted or rendered by its column. */
  readonly children: ReactNode;
}

/** Render a computed cell: its mark and its value, and the refusal of an entry once tried. */
export function ComputedCell<Row extends RowData, Sort extends string, Totals>({
  config,
  column,
  answer,
  index,
  children,
}: ComputedCellProps<Row, Sort, Totals>) {
  const t = useTranslations("grid");
  // Engaged at the first try, and for as long as the row is rendered: the trigger stays the same
  // element from then on, which the focus comes back to once the popover closes.
  const [engaged, setEngaged] = useState(false);
  const [open, setOpen] = useState(false);
  const content = (
    <>
      <Sigma role="img" aria-label={t("computed")} className="size-3 shrink-0" />
      <span className="min-w-0 truncate">{children}</span>
    </>
  );
  if (!engaged) {
    return (
      <button
        type="button"
        aria-haspopup="dialog"
        aria-expanded="false"
        className={TRIGGER}
        onClick={() => {
          setEngaged(true);
          setOpen(true);
        }}
      >
        {content}
      </button>
    );
  }
  const rows = answer();
  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger className={TRIGGER}>{content}</PopoverTrigger>
      <ComputedRefusal
        config={config}
        column={column}
        rows={rows}
        dependency={column.computed.dependsOn(rows, index)}
      />
    </Popover>
  );
}
