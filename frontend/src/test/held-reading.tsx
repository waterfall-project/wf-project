// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The reading anew that follows a write, held as Next holds it: `router.refresh()` starts a
 * transition that stays pending until the server answers. A test wraps the grid in `Reading`, makes
 * the next `refresh` of its router double a reading held (`holdReading`), and lets it go
 * (`releaseReading`), in the same commit as the rows read anew — as Next commits them — or after.
 * A module of the browser: tests of the project `dom` alone import it, each file its own reading.
 */
"use client";

import { type ReactNode, use, useEffect, useState } from "react";
import type { Mock } from "vitest";

/** How the reading of the grid rendered is suspended, and how the reading held is let go. */
const reading: { suspend?: (wait: Promise<void>) => void; resume?: () => void } = {};

/** Wrap a grid so that a reading held keeps its transition pending until `releaseReading()`. */
export function Reading({ children }: { readonly children: ReactNode }) {
  const [wait, suspend] = useState<Promise<void>>();
  useEffect(() => {
    reading.suspend = suspend;
  }, [suspend]);
  if (wait !== undefined) {
    use(wait);
  }
  return children;
}

/** Make the next calls of a router double's `refresh` readings that last until `releaseReading()`. */
export function holdReading(refresh: Mock): void {
  refresh.mockImplementation(() => {
    reading.suspend?.(
      new Promise<void>((resolve) => {
        reading.resume = resolve;
      }),
    );
  });
}

/** Let the reading held go, if one is. */
export function releaseReading(): void {
  reading.resume?.();
  delete reading.resume;
}
