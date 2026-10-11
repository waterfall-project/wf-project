// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The writes of a screen a navigation waits for (#688): a cell written, a paste applied, a command
 * pressed — each a server action whose refusal the screen tells where it was made. The navigations
 * of the page wait until it has answered, and do not take place when it was refused
 * (`held-writes.ts`, `useNavigationHold`). The screen gone, its writes hold nothing: what they
 * answer is told nowhere, and a click of the next screen does not wait for it.
 *
 * The one point every command of a screen goes through: `useHeldCommand` gives the outcome of its
 * server action, a rejection read as the screen of failure reads it (`rejected`), and holds the
 * navigations until it is known — applied when done, refused otherwise.
 */
"use client";

import { useCallback, useEffect, useRef } from "react";

import type { Outcome } from "@/api/problem";
import { holdNavigation } from "@/navigation/held-writes";

import { rejected } from "./rejection";

/**
 * Hold the navigations of the page while the writes of the screen answer — each a promise of
 * whether it was applied —, until the screen goes, or until what tells their refusal changes
 * (`scope`): a list that tells a refusal on the reading it was asked from alone releases its writes
 * once it is read otherwise, their refusal told nowhere.
 */
export function useHeldWrites(scope?: string): (write: Promise<boolean>) => void {
  const releases = useRef(new Set<() => void>());
  useEffect(() => {
    const held = releases.current;
    return () => {
      for (const release of held) {
        release();
      }
      held.clear();
    };
  }, [scope]);
  return useCallback((write: Promise<boolean>) => {
    const release = holdNavigation(write);
    releases.current.add(release);
    // An applied write holds nothing more; a refused one holds the click of its gesture, as long
    // as the screen tells it.
    void write.then(
      (applied) => {
        if (applied) {
          releases.current.delete(release);
        }
      },
      () => undefined,
    );
  }, []);
}

/**
 * The outcome of the server action of a command, a rejection read as the outcome it stands for
 * (`rejected`), the navigations of the page held until it is known — released as `useHeldWrites`
 * releases them, `scope` changed among them.
 */
export function useHeldCommand(
  scope?: string,
): <T>(command: Promise<Outcome<T>>) => Promise<Outcome<T>> {
  const hold = useHeldWrites(scope);
  return useCallback(
    <T>(command: Promise<Outcome<T>>) => {
      const outcome = command.catch(rejected);
      hold(outcome.then((answer) => answer.kind === "done"));
      return outcome;
    },
    [hold],
  );
}
