// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A header of a dense grid: the heading of its column, from the catalogue — or, in a narrow
 * column, the icon that stands for it, named by it —; the Σ that marks a column the server
 * computes whole (WF-IHM-0030), as each of its cells bears it; the sort, when the server sorts
 * it — a button; `aria-sort` on the column sorted, and on it alone —; and the handle that widens
 * it, by the pointer or by the arrows of the keyboard, a separator whose value is the width. The
 * column pinned at the end, the Gantt, has it on its left edge, where it splits the table from the
 * Gantt: dragged to the left, or moved by the left arrow, it widens the Gantt over the columns
 * before it, up to the room of the frame less the columns pinned at the start (US-0530) and the
 * widest column between, where an active cell shows (`endMaxOf`). It
 * changes a display preference alone, never a task (WF-PLA-0090).
 *
 * The header is a row of the grid, which its arrows move along (`useGridKeyboard`): the active one
 * is the one stop of the grid in the order of tabulation, its button and handle out of it
 * (WF-IHM-0100, #182). Enter or Space on it sorts its column, as its button does; Shift and the
 * left or right arrow narrow or widen it, as its handle does.
 */
"use client";

import type { RowData } from "@tanstack/react-table";
import { ArrowDown, ArrowUp, ArrowUpDown, Sigma } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  type KeyboardEvent,
  type PointerEvent,
  type ReactElement,
  type ReactNode,
  useId,
  useRef,
} from "react";

import { CommandTooltip } from "@/components/commands/command-tooltip";
import { TableHead } from "@/components/ui/table";
import { cn } from "@/components/ui/utils";

import {
  alignment,
  DIFF_MARK_KEY,
  type GridColumn,
  headingOf,
  MAX_WIDTH,
  MIN_WIDTH,
} from "./columns";
import type { CellPosition } from "./grid-keyboard";
import type { GridHeader, GridTable } from "./grid-table";
import type { Pinning } from "./pinning";

/** How far an arrow of the keyboard moves the width of a column, in pixels. */
export const RESIZE_STEP = 16;

/** The value of `aria-sort` for each state of the sort of a column. */
const ARIA_SORT = { asc: "ascending", desc: "descending" } as const;

/** What a header reads of its column: whether the server computes it whole, not its rows. */
type HeaderColumn = Pick<
  GridColumn<unknown, string, unknown>,
  "label" | "format" | "align" | "icon" | "axis" | "corner" | "help" | "helpValues"
> & {
  readonly computed?: { readonly whole: boolean };
};

/** What a header shows, and where. */
export interface HeaderCellProps<Row extends RowData> {
  readonly table: GridTable<Row>;
  readonly header: GridHeader<Row>;
  /** The column of the configuration; none for the row numbers. */
  readonly column: HeaderColumn | undefined;
  /** The classes that pin it, and its offset from the start or from the end. */
  readonly pinning: Pinning;
  /** Its place in the grid, in the row of the header. */
  readonly position: CellPosition;
  /** Whether it is the active cell of the grid, the one stop of the tabulation. */
  readonly active: boolean;
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

/** Whether a column is pinned at the end, its handle on its left edge. */
function endPinned<Row extends RowData>(header: GridHeader<Row>): boolean {
  return header.column.getIsPinned() === "end";
}

/** The widest a column gets: the room of the frame, for the column pinned at the end. */
function widestOf<Row extends RowData>(header: GridHeader<Row>): number {
  return header.column.columnDef.maxSize ?? MAX_WIDTH;
}

/** Give a column a width, within its bounds. */
function sizeTo<Row extends RowData>(
  table: GridTable<Row>,
  header: GridHeader<Row>,
  width: number,
): void {
  const bounded = Math.min(widestOf(header), Math.max(MIN_WIDTH, Math.round(width)));
  table.setColumnSizing((sizing) => ({ ...sizing, [header.column.id]: bounded }));
}

/**
 * Narrow or widen a column by a step of the keyboard, within its bounds, for the left or the
 * right arrow — the left one widening the column pinned at the end, whose handle is on its left
 * edge: whether the key was one of them.
 */
function resizeBy<Row extends RowData>(
  table: GridTable<Row>,
  header: GridHeader<Row>,
  key: string,
): boolean {
  const step = { ArrowLeft: -RESIZE_STEP, ArrowRight: RESIZE_STEP }[key];
  if (step === undefined) {
    return false;
  }
  sizeTo(table, header, header.getSize() + (endPinned(header) ? -step : step));
  return true;
}

/**
 * The drag of the handle of the column pinned at the end, on its left edge: the column widens by
 * as much as the pointer goes left of where it was pressed. The pointer is captured, so that the
 * drag goes on over the rows.
 */
function useSplitDrag<Row extends RowData>(table: GridTable<Row>, header: GridHeader<Row>) {
  const from = useRef<{ readonly x: number; readonly width: number } | undefined>(undefined);
  return {
    onPointerDown: (event: PointerEvent<HTMLElement>) => {
      if (event.button !== 0) {
        return;
      }
      event.currentTarget.setPointerCapture(event.pointerId);
      event.currentTarget.focus({ preventScroll: true });
      from.current = { x: event.clientX, width: header.getSize() };
      event.preventDefault();
    },
    onPointerMove: (event: PointerEvent<HTMLElement>) => {
      const start = from.current;
      if (start !== undefined) {
        sizeTo(table, header, start.width + start.x - event.clientX);
      }
    },
    onPointerUp: () => {
      from.current = undefined;
    },
    onPointerCancel: () => {
      from.current = undefined;
    },
  };
}

/**
 * The handle that widens a column: dragged, or moved by the arrows once it has the focus — which
 * the pointer gives it; out of the order of tabulation, the header widening its column itself. That
 * of the column pinned at the end is on its left edge, and splits the table from it.
 */
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
  const split = useSplitDrag(table, header);
  const end = endPinned(header);
  const resize = (event: KeyboardEvent) => {
    if (resizeBy(table, header, event.key)) {
      event.preventDefault();
    }
  };
  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={t("resize", { column: label })}
      aria-valuenow={size}
      aria-valuemin={MIN_WIDTH}
      aria-valuemax={widestOf(header)}
      tabIndex={-1}
      {...(end ? split : { onMouseDown: start, onTouchStart: start })}
      onKeyDown={resize}
      className={cn(
        "absolute top-0 h-full w-1.5 cursor-col-resize touch-none select-none",
        end ? "left-0" : "right-0",
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
  width,
  named,
}: {
  readonly id: string;
  readonly column: HeaderColumn | undefined;
  readonly label: string;
  /** Whether the label names the column to the readers of the screen alone: too narrow to write. */
  readonly named: boolean;
  /** The width of the column, at which an axis draws. */
  readonly width: number;
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
        <span className={column?.axis === undefined && !named ? "truncate" : "sr-only"}>
          {label}
        </span>
      ) : (
        <Icon role="img" aria-label={label} className="size-3.5 shrink-0" />
      )}
      {column?.axis?.(width)}
    </span>
  );
}

/** What a header holds in its corner besides its heading: the zoom of the Gantt; mostly nothing. */
function cornerOf(column: HeaderColumn | undefined): ReactNode {
  return column?.corner?.();
}

/**
 * A header with the definition of its column in a tooltip, which opens on the header as on its focus;
 * the header itself when the column has none.
 */
function Defined({
  column,
  label,
  children,
}: {
  readonly column: HeaderColumn | undefined;
  readonly label: string;
  readonly children: ReactElement;
}) {
  const definitions = useTranslations("columns");
  if (column?.help === undefined) {
    return children;
  }
  return (
    <CommandTooltip label={label} help={definitions(`${column.help}.help`, column.helpValues)}>
      {children}
    </CommandTooltip>
  );
}

/** Render a header of a grid. */
export function HeaderCell<Row extends RowData>({
  table,
  header,
  column,
  pinning,
  position,
  active,
}: HeaderCellProps<Row>) {
  const t = useTranslations("grid");
  const numbers =
    header.column.id === DIFF_MARK_KEY ? t("columns.diffMark") : t("columns.rowNumber");
  const label = column === undefined ? numbers : headingOf(column, (key) => t(`columns.${key}`));
  const sorted = header.column.getIsSorted();
  const align = column === undefined ? "end" : alignment(column);
  const end = align === "end";
  // The header is named by its heading alone — the Σ and the label —, not by the name of the
  // handle it holds, which would be read with every cell of the column.
  const id = useId();
  const heading = (
    <Heading
      id={id}
      column={column}
      label={label}
      width={header.getSize()}
      named={header.column.id === DIFF_MARK_KEY}
    />
  );
  const sorts = header.column.getCanSort();
  const resizes = header.column.getCanResize();
  // The keys the header itself takes, not those of its button or handle, which take their own.
  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (event.target !== event.currentTarget) {
      return;
    }
    if (sorts && (event.key === "Enter" || event.key === " ")) {
      header.column.getToggleSortingHandler()?.(event);
      event.preventDefault();
    } else if (resizes && event.shiftKey && resizeBy(table, header, event.key)) {
      event.preventDefault();
    }
  };
  const shortcuts = [
    sorts ? "Enter Space" : undefined,
    resizes ? "Shift+ArrowLeft Shift+ArrowRight" : undefined,
  ].filter((each) => each !== undefined);
  const head = (
    <TableHead
      scope="col"
      aria-labelledby={id}
      aria-sort={sorted ? ARIA_SORT[sorted] : undefined}
      aria-keyshortcuts={shortcuts.length === 0 ? undefined : shortcuts.join(" ")}
      data-row={position.row}
      data-column={position.column}
      tabIndex={active ? 0 : -1}
      onKeyDown={onKeyDown}
      style={{ left: pinning.left, right: pinning.right }}
      className={cn(
        "relative h-8 outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset",
        pinning.className,
        end ? "text-right" : null,
        align === "center" ? "text-center" : null,
      )}
    >
      {sorts ? (
        <button
          type="button"
          tabIndex={-1}
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
      {cornerOf(column)}
      {resizes ? <ResizeHandle table={table} header={header} label={label} /> : null}
    </TableHead>
  );
  return (
    <Defined column={column} label={label}>
      {head}
    </Defined>
  );
}
