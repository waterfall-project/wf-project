// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What settles the update of the own estimate of a risk in arrears (US-3140, WF-RIS-0070): the report
 * of the update is read (`getStructureRebaseReport`); it signals nothing, the update is applied
 * (`rebaseCostStructure`) without a question; it keeps a value against the project, or is refused, it
 * is handed back to be presented — to confirm, or to correct. The one reading of the report, shared
 * by the entries of the grids (`own-estimate-entry.tsx`) and by the commands of a risk, « Réexaminer »
 * and « Déclarer survenu » (`risks/own-estimate-first.tsx`): the front decides none of it but by the
 * word of the report (`signals`).
 */
"use client";

import { readRebaseReport, rebaseStructure } from "@/api/actions/revisions";
import type { Outcome } from "@/api/problem";

import { type Report, signals } from "./rebase-report";

/** What an action that gives nothing back answered, when it did not give it. */
export type Refused = Exclude<Outcome<never>, { readonly kind: "done" }>;

/** The update applied without a question, and the counter the structure moved on to. */
export interface Updated {
  readonly kind: "updated";
  readonly structureLockVersion: number;
}

/** What settling the update came to: applied, to present with the report it read, or refused. */
export type Settled =
  | Updated
  | { readonly kind: "presented"; readonly report: Report }
  | { readonly kind: "failed"; readonly outcome: Refused };

/** Read the report of the update of an own estimate, and apply it when it signals nothing. */
export async function settleOwnEstimate(
  projectId: string,
  revisionId: string,
  structureId: string,
): Promise<Settled> {
  const report = await readRebaseReport(projectId, revisionId, structureId);
  if (report.kind !== "done") {
    return { kind: "failed", outcome: report };
  }
  if (signals(report.data)) {
    return { kind: "presented", report: report.data };
  }
  const rebased = await rebaseStructure(projectId, revisionId, structureId, {
    mainStructureLockVersion: report.data.main_structure_lock_version,
    structureLockVersion: report.data.structure_lock_version,
  });
  if (rebased.kind !== "done") {
    return { kind: "failed", outcome: rebased };
  }
  return { kind: "updated", structureLockVersion: rebased.data.lock_version };
}
