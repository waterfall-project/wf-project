// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The width of the frame of a grid as the browser lays it out, for the bar above it to take: the
 * width of its table and of its borders, and of the scroll bars the system draws beside the rows
 * when it does not lay them over (#1042). And the height it may take where the screen sets it low
 * on the page (US-0710, #1209).
 */
"use client";

import { type RefObject, useLayoutEffect, useState } from "react";

/**
 * The width of an element, in pixels, kept as it changes; none before it is measured, and none
 * where the browser does not lay out (a test without a layout reads zero). The first render, on the
 * server, has no width: the bar then takes that of the table and of its two borders
 * (`barWidthOf`), which this layout effect corrects before the page is painted (#1144). The
 * observer measures again at each resize of the frame (`grid-frame.spec.ts`).
 */
export function useFrameWidth(frame: RefObject<HTMLElement | null>): number | undefined {
  const [width, setWidth] = useState<number | undefined>(undefined);
  useLayoutEffect(() => {
    const element = frame.current;
    if (element === null) {
      return undefined;
    }
    const measure = () => {
      setWidth(element.offsetWidth > 0 ? element.offsetWidth : undefined);
    };
    measure();
    if (typeof ResizeObserver === "undefined") {
      return undefined;
    }
    const observer = new ResizeObserver(measure);
    observer.observe(element);
    return () => {
      observer.disconnect();
    };
  }, [frame]);
  return width;
}

/**
 * The height a frame may take so that its foot stays in the window while the page is at its top:
 * the height of the window less where the frame starts on the page, scrolled or not. `max-h-svh`
 * bounds a frame to a window's worth from wherever it starts, which is not enough for a grid that
 * a stacked layout sets low on the page; this is the bound that is. Kept as the window and the
 * page change; none while `enabled` is false, before it is measured, and where the browser does
 * not lay out. `above` is anything that, changing, says that the frame moved down or up without the
 * page or the window changing (#2916/L4).
 */
export function useRoomBelow(
  frame: RefObject<HTMLElement | null>,
  enabled: boolean | undefined,
  above?: unknown,
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
    // What is laid above the frame without moving the page — the bar of a selection — moves its top
    // too: `above` is what tells it, and measures again.
  }, [frame, enabled, above]);
  return enabled === true ? room : undefined;
}
