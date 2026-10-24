// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a screen says in a status of its own once a command it sent is done — an object of the
 * reference data saved, a sub-project deleted, an account created —: the text, and the how-many-th
 * it is, which keys it, for the region to read out the same text said again. The one point every such
 * status goes through: each text said is noted in the history of the messages (`message-history.ts`,
 * #1043), a success, with the object it is about when the screen gives it. Two are not
 * (`noted: false`): what an unavailable command pressed lacks, said in the same region — nothing was
 * sent, no command had an outcome —, and a task handed over, which the tracker notes itself.
 */
"use client";

import { useCallback, useState } from "react";

import { useShownProjectLabel } from "@/components/shell/shown-project";

import { noteMessage } from "./message-history";

/** What the last command done said, the how-many-th it was, and what it leads to, if anything. */
export interface Said<Lead = never> {
  readonly text: string;
  readonly count: number;
  readonly lead?: Lead | undefined;
}

/** How a text is said: the object it is about, what it leads to, and whether the history notes it. */
export interface Saying<Lead = never> {
  readonly object?: string | undefined;
  readonly lead?: Lead | undefined;
  /**
   * Whether the history notes it: not for the conditions an unavailable command lacks, nothing having
   * been sent, nor for a task handed over, which the tracker notes.
   */
  readonly noted?: boolean | undefined;
}

/** Say a text in a status of its own. */
export type Say<Lead = never> = (text: string, saying?: Saying<Lead>) => void;

/**
 * What the screen said last, and the way to say the next — noted, as it is said, in the history of
 * the messages, with the project the screen shows.
 */
export function useSaid<Lead = never>(): readonly [Said<Lead> | undefined, Say<Lead>] {
  const [said, setSaid] = useState<Said<Lead>>();
  const project = useShownProjectLabel();
  const say = useCallback<Say<Lead>>(
    (text, { object, lead, noted = true } = {}) => {
      setSaid((before) => ({ text, count: (before?.count ?? 0) + 1, lead }));
      if (noted) {
        noteMessage({}, { tone: "success", sentence: text, object }, project());
      }
    },
    [project],
  );
  return [said, say];
}
