// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Where the commands of a list of the reference data tell what they could not do (WF-REF-0150,
 * EP-02/L43): a refusal of the server — the conflict (409), the object to reactivate first named
 * after the row that knows it; the version stale (412), with the offer to reload; a form whose dialog
 * is gone — is told above the list (`Reactivations`), which a cell of a dense grid has no room for;
 * and a command the server lists unavailable — a node under a deactivated parent, a role under a
 * deactivated node (WF-REF-0080), the deactivation of the default calendar (WF-REF-0120) — stays
 * presented, marked `aria-disabled` and described by the conditions it lacks, as the deletion of a
 * role an account holds is (`later-commands.tsx`): a press does not run it, and says in the region of
 * the list the conditions it lacks (`UnavailableActivation`). The commands themselves are those of
 * `commands.tsx`.
 *
 * Every prop is data — the name of the object, its commands —, never a function: a server component
 * hands it over as a client one does (défaut n° 12 de `typescript.md`). In a dense grid, the command
 * is out of the order of tabulation, the grid being one stop: Enter on its cell presses it
 * (`CELL_COMMAND`).
 */
"use client";

import { Ban, RotateCcw } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
} from "react";

import type { Outcome } from "@/api/problem";
import { useUnmet } from "@/components/commands/command";
import type { CommandOffer } from "@/components/commands/offer";
import { type ObjectNames, OutcomeNotice } from "@/components/commands/outcome-notice";
import { readingOf } from "@/navigation/pages";

import { UnavailableCellCommand } from "./cell-command";

/** The outcome of a reactivation, and the reading of the list it was asked from. */
interface Reported {
  readonly outcome: Outcome<unknown>;
  /** What the list read when the command was pressed (`readingOf`). */
  readonly reading: string;
  /** The names of the objects the refusal may be about. */
  readonly names: ObjectNames;
  /**
   * The command and the object refused — `deactivate cost_type <id>` —, whose refusal a new one of
   * them replaces rather than repeats; none for a creation, which names no object yet.
   */
  readonly target?: string | undefined;
}

/** A command that changes the state of an object of the reference data. */
type ActivationCommand = "deactivate" | "reactivate";

/**
 * What a press of an unavailable command says, the how-many-th press it was, and the reading of the
 * list it was pressed on.
 */
interface Told {
  readonly command: ActivationCommand;
  readonly name: string;
  readonly offer: CommandOffer;
  readonly press: number;
  readonly reading: string;
}

/**
 * Where a command of a list tells its refusal or the conditions it lacks, and what the list reads
 * now.
 */
interface ListReport {
  readonly report: (reported: Reported) => void;
  readonly tell: (name: string, offer: CommandOffer, command: ActivationCommand) => void;
  readonly reading: string;
  /** Give the focus to the active cell of the grid of the list, or to the list. */
  readonly refocus: () => void;
}

/** Where a reactivation tells its refusal or the conditions it lacks; none outside a list. */
const Report = createContext<ListReport | undefined>(undefined);

/**
 * Where a command of the list that holds it tells its refusal or the conditions it lacks, on the
 * reading it was pressed on; none outside a list.
 */
export function useListReport(): ListReport | undefined {
  return useContext(Report);
}

/** The cell a grid of the list keeps active, the one stop of its tabulation; none outside a grid. */
const ACTIVE_CELL = '[role="grid"] [tabindex="0"], [role="treegrid"] [tabindex="0"]';

/**
 * The region that says what the last unavailable command pressed lacks, rendered from the start so
 * that a reader of the screen hears what is put in it, and taking no room while it says nothing.
 */
function ToldConditions({ told }: { readonly told: Told | undefined }) {
  const t = useTranslations("reference.state");
  const unmet = useUnmet();
  return (
    <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
      {told === undefined ? null : (
        <span key={told.press}>
          {t(told.command === "reactivate" ? "unavailable" : "deactivationUnavailable", {
            name: told.name,
            unmet: unmet(told.offer),
          })}
        </span>
      )}
    </p>
  );
}

/** A refusal told above a list, and the key that tells it apart from the others told with it. */
interface Kept extends Reported {
  readonly key: number;
}

/**
 * A list whose objects may be reactivated, and the refusals of its commands, each told above it until
 * dismissed — one that arrives while another is told is added to it, never put in its place, save
 * the refusal of the same command on the same object, which replaces the one before —: a
 * success after them does not take them away, and the focus goes back to the active cell of the grid
 * — or to the list, ringed — once one is. What an unavailable reactivation pressed
 * lacks is said in the region of the list, on the same reading alone. A refusal is told only on the reading it
 * was asked from: an answer that arrives after the list is read otherwise — the deactivated ones
 * hidden, a search of its own — says nothing of the list now shown (défaut n° 1 de
 * `typescript.md`); a sort of another list of the screen leaves it said.
 */
export function Reactivations({
  reads,
  children,
}: {
  /** The parameters of the address the list reads (`listReads`). */
  readonly reads: readonly string[];
  readonly children: ReactNode;
}) {
  const [reported, setReported] = useState<readonly Kept[]>([]);
  const [told, setTold] = useState<Told>();
  const reading = readingOf(useSearchParams(), reads);
  const list = useRef<HTMLDivElement>(null);
  const counted = useRef(0);
  const report = useCallback((refusal: Reported) => {
    counted.current += 1;
    const key = counted.current;
    setReported((before) => [
      ...before.filter((kept) => refusal.target === undefined || kept.target !== refusal.target),
      { ...refusal, key },
    ]);
  }, []);
  const refocus = useCallback(() => {
    const cell = list.current?.querySelector<HTMLElement>(ACTIVE_CELL);
    (cell ?? list.current)?.focus();
  }, []);
  const value = useMemo(
    () => ({
      report,
      tell: (name: string, offer: CommandOffer, command: ActivationCommand) => {
        setTold((before) => ({ command, name, offer, press: (before?.press ?? 0) + 1, reading }));
      },
      reading,
      refocus,
    }),
    [reading, report, refocus],
  );
  return (
    <div
      ref={list}
      tabIndex={-1}
      className="flex min-h-0 flex-col gap-2 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <ToldConditions told={told?.reading === reading ? told : undefined} />
      {reported
        .filter((each) => each.reading === reading)
        .map((each) => (
          <OutcomeNotice
            key={each.key}
            outcome={each.outcome}
            names={each.names}
            onClear={() => {
              setReported((before) => before.filter((kept) => kept.key !== each.key));
            }}
            onDismissed={refocus}
            dismissible
          />
        ))}
      <Report value={value}>{children}</Report>
    </div>
  );
}

/**
 * The activation of an object the server lists unavailable, with the conditions it lacks
 * (`UnavailableCellCommand`): pressed, it says them in the region of the list.
 */
export function UnavailableActivation({
  command,
  name,
  offer,
}: {
  readonly command: ActivationCommand;
  readonly name: string;
  readonly offer: CommandOffer;
}) {
  const t = useTranslations("reference.state");
  const list = useContext(Report);
  return (
    <UnavailableCellCommand
      name={t(command, { name })}
      offer={offer}
      onPress={() => {
        list?.tell(name, offer, command);
      }}
    >
      {command === "reactivate" ? <RotateCcw aria-hidden="true" /> : <Ban aria-hidden="true" />}
      {t(`${command}Short`)}
    </UnavailableCellCommand>
  );
}
