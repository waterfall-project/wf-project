// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A header of a dense grid: the heading of its column, from the catalogue — or, in a narrow
 * column, the icon that stands for it, named by it —; the Σ that marks a column the server
 * computes whole (WF-IHM-0030), as each of its cells bears it; the sort, when the server sorts
 * it — a button; `aria-sort` on the column sorted, and on it alone —; and the handle that widens
 * it, by the pointer or by the arrows of the keyboard, a separator whose value is the width.
 */
"use client";

import type { RowData } from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, Sigma } from "lucide-react";
import { useTranslations } from "next-intl";
import { type KeyboardEvent, useId } from "react";

import { TableHead } from "@/components/ui/table";
import { cn } from "@/components/ui/utils";

import { alignment, type GridColumn, MAX_WIDTH, MIN_WIDTH } from "./columns";
import type { GridHeader, GridTable } from "./grid-table";

/** How far an arrow of the keyboard moves the width of a column, in pixels. */
export const RESIZE_STEP = 16;

/** The value of `aria-sort` for each state of the sort of a column. */
const ARIA_SORT = { asc: "ascending", desc: "descending" } as const;

/** What a header reads of its column: whether the server computes it whole, not its rows. */
type HeaderColumn = Pick<
  GridColumn<unknown, string, unknown>,
  "label" | "format" | "align" | "icon"
> & {
  readonly computed?: { readonly whole: boolean };
};

/** What a header shows, and where. */
export interface HeaderCellProps<Row extends RowData> {
  readonly table: GridTable<Row>;
  readonly header: GridHeader<Row>;
  /** The column of the configuration; none for the row numbers. */
  readonly column: HeaderColumn | undefined;
  /** The classes that pin it, and its offset from the start. */
  readonly pinning: { readonly className: string; readonly left: number | undefined };
}

/** The icon of the state of the sort of a column. */
function SortIcon({ state }: { readonly state: false | "asc" | "desc" }) {
  if (state === "asc") {
    return <ArrowUp aria-hidden="true" className="size-3 shrink-0" />;
  }
  if (state === "desc") {
    return <ArrowDown aria-hidden="true" className="size-3 shrink-0" />;
  }
  return <ArrowUpDown aria-hidden="true" className="size-3 shrink-0 opacity-50" />;
}

/** The handle that widens a column: dragged, or moved by the arrows once it has the focus. */
function ResizeHandle<Row extends RowData>({
  table,
  header,
  label,
}: {
  readonly table: GridTable<Row>;
  readonly header: GridHeader<Row>;
  readonly label: string;
}) {
  const t = useTranslations("grid");
  const size = header.getSize();
  const start = header.getResizeHandler();
  const resize = (event: KeyboardEvent) => {
    const step = { ArrowLeft: -RESIZE_STEP, ArrowRight: RESIZE_STEP }[event.key];
    if (step === undefined) {
      return;
    }
    event.preventDefault();
    const width = Math.min(MAX_WIDTH, Math.max(MIN_WIDTH, size + step));
    table.setColumnSizing((sizing) => ({ ...sizing, [header.column.id]: width }));
  };
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={t("resize", { column: label })}
      aria-valuenow={size}
      aria-valuemin={MIN_WIDTH}
      aria-valuemax={MAX_WIDTH}
      tabIndex={0}
      onMouseDown={start}
      onTouchStart={start}
      onKeyDown={resize}
      className={cn(
        "absolute top-0 right-0 h-full w-1.5 cursor-col-resize touch-none select-none",
        "hover:bg-border focus-visible:bg-ring focus-visible:outline-none",
        header.column.getIsResizing() ? "bg-ring" : null,
      )}
    />
  );
}

/**
 * The heading of a column: the Σ of a column the server computes whole, then its label — or the
 * icon that stands for it, named by it and shown on hover to whoever does not read its name.
 */
function Heading({
  id,
  column,
  label,
}: {
  readonly id: string;
  readonly column: HeaderColumn | undefined;
  readonly label: string;
}) {
  const t = useTranslations("grid");
  const Icon = column?.icon;
  return (
    <span
      id={id}
      title={Icon === undefined ? undefined : label}
      className="inline-flex min-w-0 items-center gap-1"
    >
      {column?.computed?.whole === true ? (
        <Sigma role="img" aria-label={t("computed")} className="size-3 shrink-0" />
      ) : null}
      {Icon === undefined ? (
        <span className="truncate">{label}</span>
      ) : (
        <Icon role="img" aria-label={label} className="size-3.5 shrink-0" />
      )}
    </span>
  );
}

/** Render a header of a grid. */
export function HeaderCell<Row extends RowData>({
  table,
  header,
  column,
  pinning,
}: HeaderCellProps<Row>) {
  const t = useTranslations("grid");
  const label = t(`columns.${column?.label ?? "rowNumber"}`);
  const sorted = header.column.getIsSorted();
  const align = column === undefined ? "end" : alignment(column);
  const end = align === "end";
  // The header is named by its heading alone — the Σ and the label —, not by the name of the
  // handle it holds, which would be read with every cell of the column.
  const id = useId();
  const heading = <Heading id={id} column={column} label={label} />;
  return (
    <TableHead
      scope="col"
      aria-labelledby={id}
      aria-sort={sorted ? ARIA_SORT[sorted] : undefined}
      style={{ left: pinning.left }}
      className={cn(
        "relative h-8 bg-muted",
        pinning.className,
        end ? "text-right" : null,
        align === "center" ? "text-center" : null,
      )}
    >
      {header.column.getCanSort() ? (
        <button
          type="button"
          onClick={header.column.getToggleSortingHandler()}
          className={cn(
            "inline-flex max-w-full items-center gap-1 rounded-sm font-medium outline-none",
            "hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring",
            end ? "flex-row-reverse" : null,
          )}
        >
          {heading}
          <SortIcon state={sorted} />
        </button>
      ) : (
        heading
      )}
      {header.column.getCanResize() ? (
        <ResizeHandle table={table} header={header} label={label} />
      ) : null}
    </TableHead>
  );
}
