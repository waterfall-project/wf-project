// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The width of the table of a dense grid, in CSS alone (US-2080, #3075): its frame takes the width
 * of its card, and its table the wider of the frame and of the sum of its columns. One column takes
 * what the card leaves — the label, the width chosen for it becoming its least —, its `<col>` given
 * no width, so that the fixed layout of the table hands it the room the others leave. No script
 * measures the frame for the layout: the table never jumps as the page loads.
 *
 * The columns pinned at the start keep the offsets their widths give them: the column that takes
 * the rest is wider than its width only when the table is no wider than its frame, which then does
 * not scroll sideways, and nothing sticks.
 *
 * The handle of the column that takes the rest reads the room of the frame the grid already keeps
 * (`useFrameRoom`), the layout never: it announces the width the column shows, starts a drag or an
 * arrow from its visible edge, and goes no narrower than what the other columns leave it
 * (`restOf`), so that its edge follows the pointer and the width it writes is the one seen.
 */
import type { RowData } from "@tanstack/react-table";

import { alignment, DIFF_MARK_KEY, type GridConfig, ROW_NUMBER_KEY } from "./columns";
import type { GridTable } from "./grid-table";

/** The key of the column of the label of a row, in every grid that has one. */
export const LABEL_KEY = "label";

/**
 * The column that takes what the card leaves: the label, when the grid shows one; else the last
 * column shown before any pinned at the end whose content is not aligned at the end — the room left
 * would open before its figures —, else the last one; so that every other column keeps the width
 * chosen for it and the room left lies at the end of the rows. Never the marks of a difference nor
 * the row numbers, which keep their width; none for a table that shows nothing else.
 */
export function stretchedColumn<Row extends RowData, Sort extends string, Totals>(
  table: GridTable<Row>,
  config: GridConfig<Row, Sort, Totals>,
): string | undefined {
  const shown = table
    .getVisibleLeafColumns()
    .filter(
      (column) =>
        column.getIsPinned() !== "end" &&
        column.id !== ROW_NUMBER_KEY &&
        column.id !== DIFF_MARK_KEY,
    );
  const atStart = shown.filter((column) => {
    const configured = config.columns.find((each) => each.key === column.id);
    return configured !== undefined && alignment(configured) !== "end";
  });
  return (shown.find((column) => column.id === LABEL_KEY) ?? atStart.at(-1) ?? shown.at(-1))?.id;
}

/** The width of the table: the wider of its frame and of the sum of its columns, as a CSS length. */
export function tableWidth<Row extends RowData>(table: GridTable<Row>): string {
  return `max(100%, ${String(table.getTotalSize())}px)`;
}

/**
 * What the other columns leave the column that takes the rest, in a frame whose rows have `room`
 * points: the narrowest it shows, whatever the width chosen for it. None when there is no such
 * column, or before the room is known — the handle then reads the width chosen.
 */
export function restOf<Row extends RowData>(
  table: GridTable<Row>,
  stretched: string | undefined,
  room: number | undefined,
): number | undefined {
  const column = stretched === undefined ? undefined : table.getColumn(stretched);
  if (column === undefined || room === undefined) {
    return undefined;
  }
  return room - (table.getTotalSize() - column.getSize());
}
