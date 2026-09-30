// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { act, fireEvent, render, renderHook, waitFor } from "@testing-library/react";
import { useRef } from "react";
import { hydrateRoot } from "react-dom/client";
import { renderToString } from "react-dom/server";
import { describe, expect, it, vi } from "vitest";

import {
  type RowWindow,
  type RowWindowControl,
  type RowWindowOptions,
  useRowWindow,
} from "./row-window";

/** The options of a window over rows, with their identity keyed as a render would key them. */
function options(rows: readonly string[]): RowWindowOptions {
  return {
    rows,
    scroller: { current: null },
    rowHeight: 28,
    edges: { start: 0, end: 0 },
    overscan: 2,
    initialRect: { width: 800, height: 280 },
    keyOf: (index) => rows[index] ?? index,
  };
}

describe("the window of the rows in view", () => {
  const rows = Array.from({ length: 100 }, (_, index) => `row-${String(index)}`);

  it("stays the same object from one render to the next when nothing scrolled, a new `keyOf` or not", () => {
    const { result, rerender } = renderHook((given: RowWindowOptions) => useRowWindow(given), {
      initialProps: options(rows),
    });
    const first = result.current;
    expect(first.items.map((item) => item.key)).toEqual(rows.slice(0, 12).map((row) => row));
    rerender(options(rows));
    rerender(options(rows));
    expect(result.current).toBe(first);
  });

  it("keys the rows anew when a new answer brings other rows", () => {
    const { result, rerender } = renderHook((given: RowWindowOptions) => useRowWindow(given), {
      initialProps: options(rows),
    });
    const other = rows.map((row) => `other-${row}`);
    rerender(options(other));
    expect(result.current.items[0]?.key).toBe("other-row-0");
    expect(result.current.after).toBe((100 - result.current.items.length) * 28);
  });

  it("leaves where it is a grid scrolled before it came alive, and shows the rows there", async () => {
    let shown: RowWindow | undefined;
    /** A grid of a hundred rows, in its element that scrolls. */
    function Grid() {
      const scroller = useRef<HTMLDivElement>(null);
      shown = useRowWindow({ ...options(rows), scroller });
      return <div ref={scroller} />;
    }
    // Rendered by the server, then scrolled by the user before the page is hydrated.
    const container = document.createElement("div");
    container.innerHTML = renderToString(<Grid />);
    document.body.append(container);
    const element = container.firstElementChild as HTMLElement;
    element.scrollTop = 1400;
    vi.spyOn(element, "offsetHeight", "get").mockReturnValue(280);
    act(() => {
      hydrateRoot(container, <Grid />);
    });
    expect(element.scrollTop).toBe(1400);
    await waitFor(() => {
      expect(shown?.items[0]?.key).toBe("row-48");
    });
    container.remove();
  });

  it("brings a row into view clear of the header above the rows and of the totals below", () => {
    let shown: RowWindowControl | undefined;
    /** A grid of a hundred rows under a header of 32 pixels, above totals of 32. */
    function Grid() {
      const scroller = useRef<HTMLDivElement>(null);
      shown = useRowWindow({ ...options(rows), scroller, edges: { start: 32, end: 32 } });
      return <div ref={scroller} />;
    }
    // The box of the element, and what it scrolls over: the header, the rows, the totals.
    vi.spyOn(HTMLElement.prototype, "offsetHeight", "get").mockReturnValue(280);
    vi.spyOn(HTMLElement.prototype, "clientHeight", "get").mockReturnValue(280);
    vi.spyOn(HTMLElement.prototype, "scrollHeight", "get").mockReturnValue(32 + 100 * 28 + 32);
    const { container } = render(<Grid />);
    const element = container.firstElementChild as HTMLElement;
    // Below the window: its foot just above the totals — 32 of header, 51 rows of 28, then the
    // 280 of the window less the 32 of the totals.
    const scrollTo = (index: number) => {
      act(() => {
        shown?.scrollToIndex(index);
        fireEvent.scroll(element);
      });
    };
    scrollTo(50);
    expect(element.scrollTop).toBe(32 + 51 * 28 - (280 - 32));
    expect(shown?.items.map((item) => item.index)).toContain(50);
    // In view already: nothing moves.
    scrollTo(48);
    expect(element.scrollTop).toBe(32 + 51 * 28 - (280 - 32));
    // Above the window: its top just below the header.
    scrollTo(10);
    expect(element.scrollTop).toBe(10 * 28);
    vi.restoreAllMocks();
  });
});
