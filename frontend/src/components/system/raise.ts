// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Raise an error from a callback no boundary sees — the end of a promise chain, a timer — to the
 * boundary of the page, which shows the screen of failure (`app/error.tsx`): the error is thrown
 * while React renders, where an error boundary catches it, instead of leaving an unhandled
 * rejection (#3111).
 */
"use client";

import { useCallback, useState } from "react";

/** The function that raises an error to the boundary of the page; stable across renders. */
export function useRaise(): (error: unknown) => void {
  const [, set] = useState();
  return useCallback((error: unknown) => {
    set(() => {
      throw error;
    });
  }, []);
}
