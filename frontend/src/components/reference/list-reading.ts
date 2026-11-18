// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Whether the list a command stands in is being read anew after a write of the list, lost once sent
 * (US-2240): the list tells it — `Reactivations` — and reads itself anew; its commands that would
 * write again wait as long (`waiting.tsx`), so that none does it again before the list shows what
 * the API did. Held apart from the list's report (`reactivation.tsx`) for the cell command
 * (`cell-command.tsx`), which that file imports, to read it.
 */
"use client";

import { createContext, useContext } from "react";

/** Whether the list is read anew after a write lost once sent. */
export const ListReading = createContext(false);

/** Whether the list the caller stands in is being read anew; never outside a list. */
export function useListReading(): boolean {
  return useContext(ListReading);
}
