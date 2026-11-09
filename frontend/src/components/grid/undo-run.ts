// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Undo and redo of a grid wired on the server (WF-IHM-0110, US-1450): the buttons, the menu and the
 * keys of `undo-commands.tsx` ask `undoLastChange` and `redoLastUndo`, the history being the
 * server's — kept by revision, by account and by session of sign-in — and never a stack of the
 * browser (WF-ARC-0070). The action reads the page anew once the server answered: the rows it
 * returned to their state, created or deleted, are the server's again, and the version the
 * structure moved on to (`NodesWritten.structure_lock_version`) is told the account, so that the
 * next write carries it.
 *
 * A change undone is one write of the structure, counted in its account like the others: the
 * gestures and the confirmation of a paste wait for it, and it waits for them (#1224). A refusal is
 * told as every screen tells one (`OutcomeNotice`), by the sentence of the catalogue its code and its
 * parameters name — the object a later change took up, the condition the history lacks, a session
 * of sign-in that carries no identifier — and stays told until it is dismissed or the next command
 * is given. A command done is announced with the depth left to undo or to redo (`remaining_depth`).
 * What is answered belongs to the structure it was sent in (défaut n° 1 de `typescript.md`).
 */
"use client";

import { useState } from "react";

import { redoLastUndo, undoLastChange } from "@/api/actions/history";
import type { Outcome } from "@/api/problem";
import { useHeldCommand } from "@/components/commands/held";

import type { StructureAccount } from "./structure-version";
import type { UndoCommand, UndoControl, UndoneCommand } from "./undo-commands";

/** The structure a grid shows: its project, its revision, the structure itself. */
interface UndoScope {
  readonly project_id: string;
  readonly revision_id: string;
  readonly structure_id: string;
}

/** What was told, and the structure it was told for. */
interface Told {
  readonly structure: string;
  readonly outcome: Outcome<unknown>;
}

/** A command done, and the structure it was done in; `count` tells the same command done again. */
interface Done extends UndoneCommand {
  readonly structure: string;
}

/**
 * Wire undo and redo on the history of the revision of a structure, whose writes `account` counts;
 * none for a grid that does not offer them (`offered`).
 */
export function useUndoRedo(
  scope: UndoScope,
  account: StructureAccount,
  offered: boolean | undefined,
): UndoControl | undefined {
  const held = useHeldCommand();
  const [told, setTold] = useState<Told>();
  const [done, setDone] = useState<Done>();
  const structure = scope.structure_id;
  const press = (command: UndoCommand) => {
    // One command at a time, and none while the structure is being written: the history the server
    // undoes is the one the writes under way are about to grow.
    if (account.busy) {
      return;
    }
    const ask = command === "undo" ? undoLastChange : redoLastUndo;
    setTold(undefined);
    setDone(undefined);
    const sent = held(ask(scope.project_id, scope.revision_id));
    account.writing(sent);
    void sent.then((outcome) => {
      if (outcome.kind === "done") {
        setDone((before) => ({
          structure,
          command,
          remaining: outcome.data.remaining_depth,
          count: (before?.count ?? 0) + 1,
        }));
        // The version the structure moved on to; a write of the structure itself (its start date,
        // its label) moves no node, and the page read anew tells its counter.
        if (outcome.data.written !== null) {
          account.reach(outcome.data.written.structure_lock_version);
        }
      } else {
        setTold({ structure, outcome });
      }
    });
  };
  if (offered !== true) {
    return undefined;
  }
  return {
    press,
    busy: account.busy,
    outcome: told?.structure === structure ? told.outcome : undefined,
    done: done?.structure === structure ? done : undefined,
    clear: () => {
      setTold(undefined);
      setDone(undefined);
    },
  };
}
