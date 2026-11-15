// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The height the frame of a grid may take where the screen sets it low on the page (US-0710,
 * #1209). Its width is no longer measured: the frame takes that of its card, and the bar above it
 * too (US-2080, #3075).
 */
"use client";

import { type RefObject, useLayoutEffect, useState } from "react";

/**
 * The height a frame may take so that its foot stays in the window while the page is at its top:
 * the height of the window less where the frame starts on the page, scrolled or not. `max-h-svh`
 * bounds a frame to a window's worth from wherever it starts, which is not enough for a grid that
 * a stacked layout sets low on the page; this is the bound that is. Kept as the window and the
 * page change; none while `enabled` is false, before it is measured, and where the browser does
 * not lay out. What the screen opens or closes above the frame without moving the page — the panel
 * of the filters, their chips — tells it by `above`, which measures again when it changes (#2916).
 */
export function useRoomBelow(
  frame: RefObject<HTMLElement | null>,
  enabled: boolean | undefined,
  above?: string,
): number | undefined {
  const [room, setRoom] = useState<number | undefined>(undefined);
  useLayoutEffect(() => {
    const element = frame.current;
    if (enabled !== true || element === null) {
      return undefined;
    }
    const measure = () => {
      if (element.offsetHeight === 0) {
        setRoom(undefined);
        return;
      }
      const top = element.getBoundingClientRect().top + window.scrollY;
      const height = Math.floor(window.innerHeight - top);
      setRoom(height > 0 ? height : undefined);
    };
    measure();
    window.addEventListener("resize", measure);
    // What lies above the frame moves its top: the page is observed, not the frame, whose own
    // height the bound changes.
    const observer =
      typeof ResizeObserver === "undefined" ? undefined : new ResizeObserver(measure);
    observer?.observe(document.body);
    return () => {
      window.removeEventListener("resize", measure);
      observer?.disconnect();
    };
  }, [frame, enabled, above]);
  return enabled === true ? room : undefined;
}
