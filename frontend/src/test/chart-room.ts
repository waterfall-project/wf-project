// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Room for the charts a component test draws. happy-dom lays nothing out: every element measures
 * nothing, and ECharts, handed a drawing of no size, warns that it cannot get its width or height,
 * then draws with no room to write a name in. A test that mounts a chart gives its drawing the size
 * a page gives it, here, and nothing else changes size: a grid beside it keeps the window it has.
 */
import { afterEach, beforeEach, type MockInstance, vi } from "vitest";

/** The size of the drawing of a chart, in pixels: as wide as a column of a screen, as high. */
export const CHART_ROOM = { width: 600, height: 300 } as const;

/** What happy-dom measures every element at: it lays nothing out. */
const NO_LAYOUT = 0;

/** Whether an element is the drawing of a chart: the box `Chart` hands ECharts, named an image. */
function isDrawing(element: HTMLElement): boolean {
  return element instanceof HTMLDivElement && element.getAttribute("role") === "img";
}

/**
 * Give the drawing of each chart the tests of a file or of a block mount the size of `CHART_ROOM`,
 * from before each test to after it; every other element measures nothing, as the document has it.
 */
export function roomForCharts(): void {
  let spies: MockInstance[] = [];
  beforeEach(() => {
    spies = (
      [
        ["clientWidth", CHART_ROOM.width],
        ["clientHeight", CHART_ROOM.height],
      ] as const
    ).map(([name, size]) => {
      return vi.spyOn(HTMLElement.prototype, name, "get").mockImplementation(function (
        this: HTMLElement,
      ) {
        return isDrawing(this) ? size : NO_LAYOUT;
      });
    });
  });
  afterEach(() => {
    for (const spy of spies) {
      spy.mockRestore();
    }
  });
}
