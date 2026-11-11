// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the history of a revision (WF-IHM-0110): the last change of the caller
 * undone (`undoLastChange`) and the last undo redone (`redoLastUndo`). The history is the server's,
 * kept by revision, by account and by session of sign-in (WF-ARC-0070): the browser keeps no stack,
 * it asks the server of Next, which calls the API (§4.3.1), and gets back the outcome the one decoder
 * makes of its answer (`src/api/problem.ts`). A change undone or redone reads the page anew: the rows
 * the server returned to their state, those it created or deleted, are the server's again.
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome } from "@/api/problem";
import { serverClient } from "@/api/server";

/** What an undo, or a redo, answers: the entry returned to its state, what was written, the depth left. */
type UndoResult = components["schemas"]["UndoResult"];

/** Read the page anew once the API has answered a change undone or redone. */
function readAnew(outcome: Outcome<UndoResult>): Outcome<UndoResult> {
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/**
 * Undo the last change of the caller on a revision (WF-IHM-0110): the API restores the nodes it
 * wrote, under the rules of the entry, and answers what it wrote with the number of changes that
 * remain to undo — or refuses it, naming the object a later change took up (`UNDO_CONFLICT`), or the
 * condition it lacks (`undo_history_not_empty`).
 */
export async function undoLastChange(
  projectId: string,
  revisionId: string,
): Promise<Outcome<UndoResult>> {
  return readAnew(
    await decode(() =>
      serverClient().POST("/projects/{project_id}/revisions/{revision_id}/undo", {
        params: { path: { project_id: projectId, revision_id: revisionId } },
      }),
    ),
  );
}

/**
 * Redo the last change the caller undid on a revision (WF-IHM-0110): the answer is that of an undo,
 * its depth the number of changes that remain to redo.
 */
export async function redoLastUndo(
  projectId: string,
  revisionId: string,
): Promise<Outcome<UndoResult>> {
  return readAnew(
    await decode(() =>
      serverClient().POST("/projects/{project_id}/revisions/{revision_id}/redo", {
        params: { path: { project_id: projectId, revision_id: revisionId } },
      }),
    ),
  );
}
