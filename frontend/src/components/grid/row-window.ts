// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The rows of a grid in view, and the space of those out of it (TanStack Virtual): a thousand
 * rows, of which a screenful and a margin are rendered, as the grid scrolls.
 *
 * The virtualizer is read as a store (`useSyncExternalStore`) whose snapshot is data — the
 * rows in view, the heights before and after them —, not through the React adapter of TanStack
 * Virtual, which hands the component an instance whose methods answer from the state it holds.
 * The React Compiler is not enabled in this front (`next.config.ts`), but the lint of React
 * refuses that adapter all the same (`react-hooks/incompatible-library`): a compiled render
 * would memoize those answers and freeze them. The snapshot changes when the window moves, and
 * only then — the same object from one render to the next otherwise.
 *
 * The height of a row is given in pixels by the grid, from the size of the root font: the rows
 * are sized in `rem`, so a font enlarged by the user enlarges them, and the window with them.
 *
 * What sticks to the edges of the element that scrolls — the header above the rows, the totals
 * below — is given too: the rows start below the header, and a row brought into view
 * (`scrollToIndex`, the active cell of the keyboard) comes out from under both.
 *
 * One row may be kept rendered wherever the window is (`kept`): the row of the active cell, which
 * holds the focus, and would drop it to the page if it were taken out as the grid scrolls. The
 * rows rendered are then not all next to one another: each comes with the height of the rows not
 * rendered just before it (`gaps`).
 */
"use client";

// The core of TanStack Virtual, pinned to its exact version: this adapter drives its lifecycle
// by `_didMount` and `_willUpdate`, which it leaves to the adapters of the frameworks and does
// not promise from one version to the next.
import {
  defaultRangeExtractor,
  elementScroll,
  observeElementOffset,
  observeElementRect,
  type Range,
  type VirtualItem,
  Virtualizer,
  type VirtualizerOptions,
} from "@tanstack/virtual-core";
import { type RefObject, useLayoutEffect, useMemo, useState, useSyncExternalStore } from "react";

/**
 * The rows rendered — those in view, and the row kept —, the height of the rows not rendered just
 * before each (`gaps`, in the order of `items`), and the heights before the first and after the
 * last.
 */
export interface RowWindow {
  readonly items: readonly VirtualItem[];
  readonly gaps: readonly number[];
  readonly before: number;
  readonly after: number;
}

/** The rows in view, and how to bring a row into view, out from under the header and totals. */
export interface RowWindowControl extends RowWindow {
  readonly scrollToIndex: (index: number) => void;
}

/** The identity of a row. */
type RowKey = string | number;

/** What the window is computed from. */
export interface RowWindowOptions {
  /** The rows, whose identity tells a new answer from the same one rendered again. */
  readonly rows: readonly unknown[];
  /** The element that scrolls. */
  readonly scroller: RefObject<HTMLElement | null>;
  /** The height of a row, in pixels, the same for every one. */
  readonly rowHeight: number;
  /** The heights, in pixels, of what sticks above the rows and below them: header, totals. */
  readonly edges: { readonly start: number; readonly end: number };
  /** The rows rendered beyond those in view, at each end. */
  readonly overscan: number;
  /** The size assumed before the element is measured — on the server, among others. */
  readonly initialRect: { readonly width: number; readonly height: number };
  /** The identity of the row at an index, stable from one answer to the next. */
  readonly keyOf: (index: number) => RowKey;
  /** The index of a row rendered wherever the window is — the row of the active cell —, if any. */
  readonly kept?: number | undefined;
}

type RowVirtualizer = Virtualizer<HTMLElement, HTMLElement>;

/**
 * The window of a virtualizer, whose rows start below the header (`scrollMargin`): the heights
 * before and after the rows in view are counted from the first row.
 */
function windowOf(virtualizer: RowVirtualizer): RowWindow {
  const items = virtualizer.getVirtualItems();
  const margin = virtualizer.options.scrollMargin;
  return {
    items,
    gaps: items.map((item, index) => item.start - (items[index - 1]?.end ?? margin)),
    before: (items[0]?.start ?? margin) - margin,
    after: virtualizer.getTotalSize() - ((items.at(-1)?.end ?? margin) - margin),
  };
}

/** A virtualizer, and its window as a store React subscribes to. */
class RowWindowStore {
  readonly virtualizer: RowVirtualizer;
  private snapshot: RowWindow;
  private readonly listeners = new Set<() => void>();
  private options: RowWindowOptions;
  // The virtualizer computes its measurements anew when the function that keys its rows
  // changes: it is made again when the rows or their height change, and only then — a new
  // `keyOf` at every render would make it measure everything at every render.
  private itemKey: (index: number) => RowKey;
  // Made again when the row kept changes, and only then: the virtualizer computes the rows it
  // renders anew when its extractor changes.
  private extractor: (range: Range) => number[];

  constructor(options: RowWindowOptions) {
    this.options = options;
    this.itemKey = this.keyer();
    this.extractor = this.keeper();
    this.virtualizer = new Virtualizer(this.resolve());
    this.snapshot = windowOf(this.virtualizer);
  }

  /** Take the options of a render — a new answer, another height —, and the window they make. */
  update(options: RowWindowOptions): void {
    const before = this.options;
    this.options = options;
    if (options.rows !== before.rows || options.rowHeight !== before.rowHeight) {
      this.itemKey = this.keyer();
    }
    if (options.kept !== before.kept) {
      this.extractor = this.keeper();
    }
    this.virtualizer.setOptions(this.resolve());
    this.refresh();
  }

  /**
   * Follow the element that scrolls, after a render. When it is first found, the offset the
   * virtualizer took while rendering — before the element was there, so none — is dropped, and
   * read from the element: attaching would otherwise scroll it back to the top.
   */
  attach(): void {
    if (this.virtualizer.scrollElement !== this.options.scroller.current) {
      this.virtualizer.scrollOffset = null;
    }
    this.virtualizer._willUpdate();
  }

  readonly subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  readonly getSnapshot = (): RowWindow => this.snapshot;

  /** Bring a row into view, as little as it takes, clear of what sticks at the edges. */
  readonly scrollToIndex = (index: number): void => {
    this.virtualizer.scrollToIndex(index, { align: "auto" });
  };

  /** The rows to render: those of the range, and the row kept among them, in their order. */
  private keeper(): (range: Range) => number[] {
    const kept = this.options.kept;
    return (range) => {
      const indexes = defaultRangeExtractor(range);
      if (kept === undefined || kept >= range.count || indexes.includes(kept)) {
        return indexes;
      }
      return [...indexes, kept].sort((a, b) => a - b);
    };
  }

  /** A function that keys the rows by the `keyOf` of the last render. */
  private keyer(): (index: number) => RowKey {
    return (index) => this.options.keyOf(index);
  }

  /** Keep the window the virtualizer computes, when it moved: the same one otherwise. */
  private refresh(): boolean {
    const next = windowOf(this.virtualizer);
    const moved =
      next.items !== this.snapshot.items ||
      next.before !== this.snapshot.before ||
      next.after !== this.snapshot.after;
    if (moved) {
      this.snapshot = next;
    }
    return moved;
  }

  private readonly notify = (): void => {
    if (this.refresh()) {
      for (const listener of this.listeners) {
        listener();
      }
    }
  };

  private readonly scrollElement = (): HTMLElement | null => this.options.scroller.current;

  private readonly estimateSize = (): number => this.options.rowHeight;

  // Where the element already is: a grid scrolled before the page came alive — rendered by the
  // server, not yet hydrated — stays where the user took it.
  private readonly initialOffset = (): number => this.options.scroller.current?.scrollTop ?? 0;

  private resolve(): VirtualizerOptions<HTMLElement, HTMLElement> {
    return {
      count: this.options.rows.length,
      getScrollElement: this.scrollElement,
      estimateSize: this.estimateSize,
      overscan: this.options.overscan,
      initialRect: this.options.initialRect,
      initialOffset: this.initialOffset,
      scrollMargin: this.options.edges.start,
      scrollPaddingStart: this.options.edges.start,
      scrollPaddingEnd: this.options.edges.end,
      getItemKey: this.itemKey,
      rangeExtractor: this.extractor,
      observeElementRect,
      observeElementOffset,
      scrollToFn: elementScroll,
      onChange: this.notify,
    };
  }
}

/**
 * The rows of a grid in view, as it scrolls and as it is resized, and how to bring one into view:
 * as little as it takes, clear of the header and of the totals.
 */
export function useRowWindow(options: RowWindowOptions): RowWindowControl {
  const [store] = useState(() => new RowWindowStore(options));
  store.update(options);
  useLayoutEffect(() => store.virtualizer._didMount(), [store]);
  useLayoutEffect(() => {
    store.attach();
  });
  const shown = useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);
  return useMemo(() => ({ ...shown, scrollToIndex: store.scrollToIndex }), [shown, store]);
}

/** The size of the root font before the browser tells it: the default of the browsers. */
const DEFAULT_FONT_SIZE = 16;

/** Follow what may change the size of the root font: a zoom resizes the window. */
function subscribeToResize(listener: () => void): () => void {
  window.addEventListener("resize", listener);
  return () => {
    window.removeEventListener("resize", listener);
  };
}

/** The size of the root font, in pixels, as the browser computes it. */
function computedFontSize(): number {
  const size = Number.parseFloat(getComputedStyle(document.documentElement).fontSize);
  return Number.isFinite(size) && size > 0 ? size : DEFAULT_FONT_SIZE;
}

/** The size of the root font, in pixels: its default on the server. */
export function useRootFontSize(): number {
  return useSyncExternalStore(subscribeToResize, computedFontSize, () => DEFAULT_FONT_SIZE);
}
