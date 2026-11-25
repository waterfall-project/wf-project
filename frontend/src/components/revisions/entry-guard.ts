// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What stands between a grid and its writes when the structure it reads must be updated first
 * (US-3140): the own estimate of a risk in arrears, which the service refuses every entry on
 * (`own_estimate_up_to_date`, WF-RIS-0070). A write of the grid goes through `useEntryGuard` — the
 * write alone where nothing stands in the way — and the guard, provided by `own-estimate-entry.tsx`,
 * reads the report of the update, applies it when it signals nothing, and then writes the entry as
 * the user made it: from the nodes read again after the update, the counter of the node and of the
 * structure being theirs, which the update rewrote (`Entry`). A write that offers no way to be built
 * again is withheld, told as the service would tell it (`withheld`); so is any write when the report
 * signals, which the screen presents to confirm or to correct.
 */
"use client";

import { createContext, useContext } from "react";

import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";

type NodesWritten = components["schemas"]["NodesWritten"];
type EditableField = components["schemas"]["EditableField"];

/** A node read again after the update of its structure: its counter, and the fields it accepts. */
export interface FreshNode {
  readonly lock_version: number;
  readonly editable_fields: readonly EditableField[];
}

/** The nodes of a structure read again after its update, and the counter the structure moved on to. */
export interface Fresh {
  readonly nodes: ReadonlyMap<string, FreshNode>;
  /** The counter of the structure, which a paste carries. */
  readonly structureLockVersion: number;
}

/**
 * An entry the guard can write again once the structure is updated: what it is about, and how it is
 * sent. `send` is called without `fresh` where nothing stands in the way — the grid's own counters
 * —, and with it for the entry held back, which then takes the counters read again.
 */
export interface Entry<T extends NodesWritten> {
  /** The nodes the entry writes into; none for a block pasted, which the service places. */
  readonly nodes: readonly string[];
  /** The fields entered, which each of those nodes must still accept (`editable_fields`). */
  readonly fields: readonly string[];
  readonly send: (fresh?: Fresh) => Promise<Outcome<T>>;
}

/** Let a write go once the structure is up to date, or say why it does not. */
export interface EntryGuard {
  <T>(write: () => Promise<Outcome<T>>): Promise<Outcome<T>>;
  <T extends NodesWritten>(entry: (() => Promise<Outcome<T>>) | Entry<T>): Promise<Outcome<T>>;
}

/** No guard: the write goes as it is. */
const UNGUARDED: EntryGuard = <T>(write: (() => Promise<Outcome<T>>) | Entry<NodesWritten>) =>
  typeof write === "function" ? write() : write.send();

const GuardContext = createContext<EntryGuard>(UNGUARDED);

/** The counter of a node to write: the one read again after the update, or the grid's own. */
export function counterOf(fresh: Fresh | undefined, nodeId: string, own: number): number {
  return fresh?.nodes.get(nodeId)?.lock_version ?? own;
}

/** The fields a change enters, as a node names them among those it accepts: `task.label`. */
export function fieldsOf(facet: "task" | "estimate_line", change: object): string[] {
  return Object.keys(change).map((key) => `${facet}.${key}`);
}

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

/**
 * The refusal of an entry whose node the update removed, as the service tells a node it does not have
 * (`NOT_FOUND`): nothing is written, and the grid tells it where the entry was made — the one message
 * of the entry, the screen saying apart that the own estimate was updated.
 */
export function notFound<T>(): Outcome<T> {
  return {
    kind: "refused",
    problem: { code: "NOT_FOUND", status: 404 },
    conflictingObjectId: null,
  };
}

/**
 * The refusal of an entry into a field its node no longer accepts once updated, as the service tells
 * it (`VALIDATION_FAILED`, `FIELD_NOT_ACCEPTED` on the field of the body): nothing is written, and the
 * grid tells it on the cell, the one message of the entry.
 */
export function notAccepted<T>(field: string): Outcome<T> {
  return {
    kind: "refused",
    problem: {
      code: "VALIDATION_FAILED",
      status: 422,
      fields: [{ pointer: `/${field.slice(field.indexOf(".") + 1)}`, code: "FIELD_NOT_ACCEPTED" }],
    },
    conflictingObjectId: null,
  };
}
