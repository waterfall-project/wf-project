// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The width of the frame of a grid as the browser lays it out, for the bar above it to take: the
 * width of its table and of its borders, and of the scroll bars the system draws beside the rows
 * when it does not lay them over (#1042).
 */
"use client";

import { type RefObject, useLayoutEffect, useState } from "react";

/**
 * The width of an element, in pixels, kept as it changes; none before it is measured, and none
 * where the browser does not lay out (a test without a layout reads zero).
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
