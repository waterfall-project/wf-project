// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The columns of a dense grid that stay where they are as it scrolls sideways: the identifying
 * ones at its start (WF-IHM-0060), and, in a grid that asks for it, one at its end — the Gantt of
 * the planning (US-0530) —, which slides over the columns before it as it widens, as in Microsoft
 * Project. Those it covers stay within reach of the scroll: the grid scrolls them out from under it,
 * between the columns pinned at each edge (`scroll-padding`).
 *
 * The column pinned at the end widens up to the room the frame of the grid has at its widest
 * (`useFrameRoom`), less the columns pinned at the start, which it never covers, and less the
 * widest column between them, which the active cell scrolls out from under it (`endMaxOf`).
 */
"use client";

import type { RowData } from "@tanstack/react-table";
import { type RefObject, useLayoutEffect, useState } from "react";

import { cn } from "@/components/ui/utils";

import type { GridTable } from "./grid-table";

/** How a cell of a column is pinned: its classes, and its offset from the start or from the end. */
export interface Pinning {
  readonly className: string;
  readonly left: number | undefined;
  readonly right: number | undefined;
}

/** How a column of the table is pinned, at a layer above the cells it slides over. */
export function pinningOf<Row extends RowData>(
  table: GridTable<Row>,
  id: string,
  layer: string,
): Pinning {
  const column = table.getColumn(id);
  const pinned = column?.getIsPinned();
  if (column === undefined || pinned === false || pinned === undefined) {
    return { className: "", left: undefined, right: undefined };
  }
  if (pinned === "end") {
    const first = table.getEndVisibleLeafColumns().at(0)?.id === id;
    return {
      className: cn("sticky", layer, first ? "border-l" : null),
      left: undefined,
      right: column.getAfter("end"),
    };
  }
  const last = table.getStartVisibleLeafColumns().at(-1)?.id === id;
  return {
    className: cn("sticky", layer, last ? "border-r" : null),
    left: column.getStart("start"),
    right: undefined,
  };
}

/** The width of the columns pinned at the start, which the other columns slide under. */
export function pinnedWidth<Row extends RowData>(table: GridTable<Row>): number {
  return table.getStartVisibleLeafColumns().reduce((width, column) => width + column.getSize(), 0);
}

/** The width of the columns pinned at the end, which slide over the others. */
export function endPinnedWidth<Row extends RowData>(table: GridTable<Row>): number {
  return table.getEndVisibleLeafColumns().reduce((width, column) => width + column.getSize(), 0);
}

/**
 * The room the rows of a grid have at the widest its frame gets — the width of what holds the
 * frame, less the borders and the scroll bar of the frame —, kept as it changes; none before it is
 * measured, and none where the browser does not lay out.
 */
export function useFrameRoom(frame: RefObject<HTMLElement | null>): number | undefined {
  const [room, setRoom] = useState<number | undefined>(undefined);
  useLayoutEffect(() => {
    const element = frame.current;
    const holder = element?.parentElement;
    if (element === null || holder === null || holder === undefined) {
      return undefined;
    }
    const measure = () => {
      const width = holder.clientWidth - (element.offsetWidth - element.clientWidth);
      setRoom(width > 0 ? width : undefined);
    };
    measure();
    if (typeof ResizeObserver === "undefined") {
      return undefined;
    }
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    observer.observe(holder);
    return () => {
      observer.disconnect();
    };
  }, [frame]);
  return room;
}
