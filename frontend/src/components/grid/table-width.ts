// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The width of the table of a dense grid, in CSS alone (US-2080, #3075): its frame takes the width
 * of its card, and its table the wider of the frame and of the sum of its columns. One column takes
 * what the card leaves — the label, the width chosen for it becoming its least —, its `<col>` given
 * no width, so that the fixed layout of the table hands it the room the others leave. No script
 * measures the frame: the table never jumps as the page loads.
 *
 * The columns pinned at the start keep the offsets their widths give them: the column that takes
 * the rest is wider than its width only when the table is no wider than its frame, which then does
 * not scroll sideways, and nothing sticks.
 */
import type { RowData } from "@tanstack/react-table";

import { DIFF_MARK_KEY, ROW_NUMBER_KEY } from "./columns";
import type { GridTable } from "./grid-table";

/** The key of the column of the label of a row, in every grid that has one. */
export const LABEL_KEY = "label";

/**
 * The column that takes what the card leaves: the label, when the grid shows one; else the last
 * column shown before any pinned at the end, so that every other column keeps the width chosen for
 * it and the room left lies at the end of the rows. Never the marks of a difference nor the row
 * numbers, which keep their width; none for a table that shows nothing else.
 */
export function stretchedColumn<Row extends RowData>(table: GridTable<Row>): string | undefined {
  const shown = table
    .getVisibleLeafColumns()
    .filter(
      (column) =>
        column.getIsPinned() !== "end" &&
        column.id !== ROW_NUMBER_KEY &&
        column.id !== DIFF_MARK_KEY,
    );
  return (shown.find((column) => column.id === LABEL_KEY) ?? shown.at(-1))?.id;
}

/** The width of the table: the wider of its frame and of the sum of its columns, as a CSS length. */
export function tableWidth<Row extends RowData>(table: GridTable<Row>): string {
  return `max(100%, ${String(table.getTotalSize())}px)`;
}
