// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The rows of a grid in view, and the space of those out of it (TanStack Virtual): a thousand
 * rows, of which a screenful and a margin are rendered, as the grid scrolls.
 *
 * The virtualizer is read as a store (`useSyncExternalStore`) whose snapshot is data — the
 * rows in view, the heights before and after them —, not through the React adapter of TanStack
 * Virtual: that one hands the component an instance whose methods answer from the state it
 * holds, which the React Compiler would memoize and freeze (`react-hooks/incompatible-library`).
 * The snapshot changes when the virtualizer says its window moved, and only then.
 */
"use client";

import {
  elementScroll,
  observeElementOffset,
  observeElementRect,
  type VirtualItem,
  Virtualizer,
  type VirtualizerOptions,
} from "@tanstack/react-virtual";
import { type RefObject, useLayoutEffect, useState, useSyncExternalStore } from "react";

/** The rows in view, and the heights of the rows out of view before and after them. */
export interface RowWindow {
  readonly items: readonly VirtualItem[];
  readonly before: number;
  readonly after: number;
}

/** What the window is computed from. */
export interface RowWindowOptions {
  /** The number of rows. */
  readonly count: number;
  /** The element that scrolls. */
  readonly scroller: RefObject<HTMLElement | null>;
  /** The height of a row, in pixels, the same for every one. */
  readonly rowHeight: number;
  /** The rows rendered beyond those in view, at each end. */
  readonly overscan: number;
  /** The size assumed before the element is measured — on the server, among others. */
  readonly initialRect: { readonly width: number; readonly height: number };
  /** The identity of the row at an index, stable from one answer to the next. */
  readonly keyOf: (index: number) => string | number;
}

type RowVirtualizer = Virtualizer<HTMLElement, HTMLElement>;

/** The window of a virtualizer. */
function windowOf(virtualizer: RowVirtualizer): RowWindow {
  const items = virtualizer.getVirtualItems();
  return {
    items,
    before: items[0]?.start ?? 0,
    after: virtualizer.getTotalSize() - (items.at(-1)?.end ?? 0),
  };
}

/** A virtualizer, and its window as a store React subscribes to. */
class RowWindowStore {
  readonly virtualizer: RowVirtualizer;
  private snapshot: RowWindow;
  private readonly listeners = new Set<() => void>();

  constructor(options: RowWindowOptions) {
    this.virtualizer = new Virtualizer(this.resolve(options));
    this.snapshot = windowOf(this.virtualizer);
  }

  /** Take the options of a render — a new answer, another count —, and the window they make. */
  update(options: RowWindowOptions): void {
    this.virtualizer.setOptions(this.resolve(options));
    this.refresh();
  }

  readonly subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => {
      this.listeners.delete(listener);
    };
  };

  readonly getSnapshot = (): RowWindow => this.snapshot;

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

  private resolve(options: RowWindowOptions): VirtualizerOptions<HTMLElement, HTMLElement> {
    return {
      count: options.count,
      getScrollElement: () => options.scroller.current,
      estimateSize: () => options.rowHeight,
      overscan: options.overscan,
      initialRect: options.initialRect,
      getItemKey: options.keyOf,
      observeElementRect,
      observeElementOffset,
      scrollToFn: elementScroll,
      onChange: () => {
        if (this.refresh()) {
          for (const listener of this.listeners) {
            listener();
          }
        }
      },
    };
  }
}

/** The rows of a grid in view, as it scrolls and as it is resized. */
export function useRowWindow(options: RowWindowOptions): RowWindow {
  const [store] = useState(() => new RowWindowStore(options));
  store.update(options);
  useLayoutEffect(() => store.virtualizer._didMount(), [store]);
  useLayoutEffect(() => {
    store.virtualizer._willUpdate();
  });
  return useSyncExternalStore(store.subscribe, store.getSnapshot, store.getSnapshot);
}
