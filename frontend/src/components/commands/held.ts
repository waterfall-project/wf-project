// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The writes of a screen a navigation waits for (#688): a cell written, a paste applied, a command
 * pressed — each a server action whose refusal the screen tells where it was made. The navigations
 * of the page wait until it has answered, and do not take place when it was refused
 * (`held-writes.ts`, `useNavigationHold`). The screen gone, or the list that tells their refusal
 * read otherwise, its writes hold nothing: a click does not wait for them, and one refused after is
 * told by the bar of the shell, unless what asked it tells it still (`LeftRefusals`, #863).
 *
 * The one point every command of a screen goes through: `useHeldCommand` gives the outcome of its
 * server action, a rejection read as the screen of failure reads it (`rejected`), and holds the
 * navigations until it is known — applied when done, refused otherwise.
 */
"use client";

import { useCallback, useEffect, useRef } from "react";

import type { Outcome } from "@/api/problem";
import { shownScreen } from "@/components/notices/message-history";
import { useShownProjectLabel } from "@/components/shell/shown-project";
import { holdNavigation, wasApplied, type WriteAnswer } from "@/navigation/held-writes";

import { rejected } from "./rejection";

/**
 * Hold the navigations of the page while the writes of the screen answer — each a promise of
 * whether it was applied, or of its outcome —, until the screen goes, or until what tells their
 * refusal changes (`scope`): a list that tells a refusal on the reading it was asked from alone
 * releases its writes once it is read otherwise. A write refused once released is told by the bar
 * of the shell, and noted with the screen it was made on, unless `told` — given with the write, read
 * as the refusal arrives — says that what asked it tells it still: a dialog left open over the list,
 * at its fields.
 */
export function useHeldWrites(
  scope?: string,
): (write: Promise<WriteAnswer>, told?: () => boolean) => void {
  const releases = useRef(new Set<() => void>());
  const project = useShownProjectLabel();
  useEffect(() => {
    const held = releases.current;
    return () => {
      for (const release of held) {
        release();
      }
      held.clear();
    };
  }, [scope]);
  return useCallback(
    (write: Promise<WriteAnswer>, told?: () => boolean) => {
      const release = holdNavigation(write, told, shownScreen(project()));
      releases.current.add(release);
      // An applied write holds nothing more; a refused one holds the click of its gesture, as long
      // as the screen tells it.
      void write.then(
        (answer) => {
          if (wasApplied(answer)) {
            releases.current.delete(release);
          }
        },
        () => undefined,
      );
    },
    [project],
  );
}

/**
 * The outcome of the server action of a command, a rejection read as the outcome it stands for
 * (`rejected`), the navigations of the page held until it is known — released as `useHeldWrites`
 * releases them, `scope` changed among them, and its refusal once released told by the bar of the
 * shell unless `told` says that what asked it tells it still.
 */
export function useHeldCommand(
  scope?: string,
): <T>(command: Promise<Outcome<T>>, told?: () => boolean) => Promise<Outcome<T>> {
  const hold = useHeldWrites(scope);
  return useCallback(
    <T>(command: Promise<Outcome<T>>, told?: () => boolean) => {
      const outcome = command.catch(rejected);
      hold(outcome, told);
      return outcome;
    },
    [hold],
  );
}
