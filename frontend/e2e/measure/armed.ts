// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The script a step in place runs in the page to watch its grid (`steps.ts`), apart from Playwright
 * so that a unit test runs it on a document (`armed.test.ts`).
 */
import type { Reached } from "../usable";

/** What a grid changed in place shows once the gesture is served. */
export interface Expected {
  /** The name of the grid. */
  readonly grid: string;
  /** What the address of the reading holds, for a gesture that reads the grid anew. */
  readonly query?: string;
  /** The cell written, by the `aria-rowindex` of its row and its position: what it shows then. */
  readonly cell?: {
    readonly row: number;
    readonly column: number;
    readonly shows?: string;
    readonly differsFrom?: string;
    /**
     * The position of a cell of the same row that bears the sign of a difference to the base
     * (`BaseMark`): in a grid compared, the marks read anew after the write, which its answer
     * took away from the row.
     */
    readonly marked?: number;
  };
}

/** The arguments of the script that watches a grid changed in place. */
export interface Watch {
  readonly reached: string;
  readonly armed: string;
  readonly expected: Expected;
}

/**
 * Run in the page before a gesture in place: watch every frame until the grid is usable and shows
 * what the gesture asked, and write the moment, on the clock of the operating system.
 * Self-contained: Playwright hands its source to the page.
 */
export function armUsable({ reached: reachedName, armed, expected }: Watch): void {
  const tests = (window as unknown as Record<string, Reached>)[reachedName];
  const slot = window as unknown as Record<string, number | null>;
  slot[armed] = null;
  // The watch of a gesture before, whose grid never showed what it asked, stops at this one's.
  const generation = performance.now();
  slot[`${armed}:generation`] = generation;
  if (tests === undefined) {
    return;
  }
  // Whether a cell of a row bears the sign of a difference to the base (`base-mark.tsx`, "Δ"),
  // when one is asked: written here, the script being self-contained.
  const marked = (row: Element | null, column: number | undefined): boolean =>
    column === undefined ||
    (row instanceof HTMLTableRowElement &&
      (row.cells.item(column)?.textContent ?? "").includes("Δ"));
  const shows = (grid: Element): boolean => {
    if (expected.query !== undefined && !window.location.search.includes(expected.query)) {
      return false;
    }
    const { cell: wanted } = expected;
    if (wanted === undefined) {
      // Drawn in place: the header, the totals and the first row within the height of the window —
      // a grid sorted by a column far to the right has scrolled sideways to it, and stays so.
      return ["thead th", "tfoot td", 'tbody tr[aria-rowindex="2"] td'].every((selector) => {
        const box = grid.querySelector(selector)?.getBoundingClientRect();
        return box !== undefined && box.height > 0 && box.top >= 0 && box.bottom <= innerHeight;
      });
    }
    const row = grid.querySelector(`tbody tr[aria-rowindex="${String(wanted.row)}"]`);
    const cell = row instanceof HTMLTableRowElement ? row.cells.item(wanted.column) : null;
    const text = cell?.textContent ?? "";
    return (
      cell !== null &&
      grid.querySelector("input, textarea") === null &&
      tests.inWindow(cell) &&
      (wanted.shows === undefined || text.includes(wanted.shows)) &&
      (wanted.differsFrom === undefined || text !== wanted.differsFrom) &&
      marked(row, wanted.marked)
    );
  };
  const frame = () => {
    if (slot[`${armed}:generation`] !== generation) {
      return;
    }
    const grid = document.querySelector(`[role="treegrid"][aria-label="${expected.grid}"]`);
    if (
      grid !== null &&
      grid.getAttribute("aria-busy") !== "true" &&
      tests.hydrated(grid) &&
      shows(grid)
    ) {
      slot[armed] = performance.timeOrigin + performance.now();
      return;
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}
