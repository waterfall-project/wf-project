// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The script that watches a screen of the project until it is usable (US-2420,
 * `project-screens.ts`), run in the page before the click: Playwright hands its source to the page,
 * so it is self-contained, and its test (`screen-watch.test.ts`) plays it in a document.
 */

/** A section of a screen the script waits for, by the name the page gives it. */
export interface Watched {
  readonly name: string;
  /** Whether it holds a chart, which is hydrated and drawn before the section is usable. */
  readonly chart: boolean;
  /**
   * The source of the pattern of the sentence the section says in place of its chart when the
   * project has nothing to draw: without it, a section with no chart drawn is never usable.
   */
  readonly empty?: string;
  /** Whether its top, or its chart's, must lie within the window. */
  readonly windowed: boolean;
}

/** The arguments of the script that watches a screen. */
export interface Watch {
  readonly sections: readonly Watched[];
  /** The source of the pattern of the address of the screen, tried on its path and its query. */
  readonly address: string;
  readonly armed: string;
}

/**
 * Run in the page before the click: watch every frame until the address is the screen's and each
 * section, sought under the `main` of the page, is usable; write the moment, on the clock of the
 * operating system. A section of a chart is usable once hydrated — React has taken over its
 * element, whatever it holds — and in one of its two states: the chart drawn, or, when the project
 * has nothing to draw, the sentence that says so (`empty`, a paragraph of the section that matches
 * it: any other paragraph is no reason to take the section before its chart is drawn).
 */
export function armScreen({ sections, address, armed }: Watch): void {
  const slot = window as unknown as Record<string, number | null>;
  slot[armed] = null;
  const hydrated = (element: Element) =>
    Object.keys(element).some((key) => key.startsWith("__reactProps$"));
  const within = (element: Element) => {
    const box = element.getBoundingClientRect();
    return box.top >= 0 && box.top < innerHeight;
  };
  const here = () => new RegExp(address).test(location.pathname + location.search);
  const usable = ({ name, chart, windowed, empty }: Watched): boolean => {
    const section = document.querySelector(
      `main section[aria-label="${name}"], main [role="region"][aria-label="${name}"]`,
    );
    if (section === null) {
      return false;
    }
    if (!chart) {
      return !windowed || within(section);
    }
    if (!hydrated(section)) {
      return false;
    }
    const drawn = section.querySelector('[role="img"]');
    if (drawn === null) {
      const said = empty === undefined ? null : new RegExp(empty);
      return (
        said !== null &&
        Array.from(section.querySelectorAll("p")).some((p) => said.test(p.textContent))
      );
    }
    return drawn.querySelector("svg path") !== null && (!windowed || within(drawn));
  };
  const frame = () => {
    if (here() && sections.every(usable)) {
      slot[armed] = performance.timeOrigin + performance.now();
      return;
    }
    requestAnimationFrame(frame);
  };
  requestAnimationFrame(frame);
}
