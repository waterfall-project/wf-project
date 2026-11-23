// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What stands between a grid and its writes when the structure it reads must be updated first
 * (US-3140): the own estimate of a risk in arrears, which the service refuses every entry on
 * (`own_estimate_up_to_date`, WF-RIS-0070). A write of the grid goes through `useEntryGuard` — the
 * write alone where nothing stands in the way — and the guard, provided by `own-estimate-entry.tsx`,
 * reads the report of the update, applies it when it signals nothing, and then lets the write go; when
 * it signals, it presents the report to confirm or to correct, and the write is withheld, told as the
 * service would tell it (`withheld`).
 */
"use client";

import { createContext, useContext } from "react";

import type { Outcome } from "@/api/problem";

/** Let a write go once the structure is up to date, or say why it does not. */
export type EntryGuard = <T>(write: () => Promise<Outcome<T>>) => Promise<Outcome<T>>;

/** No guard: the write goes as it is. */
const UNGUARDED: EntryGuard = (write) => write();

const GuardContext = createContext<EntryGuard>(UNGUARDED);

/** The provider of the guard of the structure a grid reads. */
export const EntryGuardProvider = GuardContext.Provider;

/** The guard a write of the grid goes through; the write itself where none is provided. */
export function useEntryGuard(): EntryGuard {
  return useContext(GuardContext);
}

/**
 * The refusal of a write the update withholds, as the service words its own (`STATE_FORBIDS_OPERATION`,
 * `own_estimate_up_to_date`): the screen says it through the notice of the write, and presents the
 * report of the update by its side.
 */
export function withheld<T>(): Outcome<T> {
  return {
    kind: "conflict",
    problem: {
      code: "STATE_FORBIDS_OPERATION",
      status: 409,
      params: { missing_condition: "own_estimate_up_to_date" },
    },
    conflictingObjectId: null,
  };
}
