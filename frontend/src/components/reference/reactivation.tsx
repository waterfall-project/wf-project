// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The state of an object of the reference data in a list, and its reactivation (WF-REF-0150): a
 * deactivated object, which the list shows when the address asks for the deactivated ones too,
 * offers to reactivate it to a session that may modify its part of the reference — the permission
 * of modification of the function (`platformOffer`), the rule of the catalogue (WF-ADM-0100). The
 * command asks the operation the contract gives each kind of object (`reactivate`), from the version
 * read; the page is then read anew. Its refusal is told above the list (`Reactivations`), which a
 * cell of a dense grid has no room for.
 *
 * WF-REF-0080 reactivates a node only under an active parent, and a role only under an active node;
 * the contract declares neither that refusal nor whether the command is available (#532): the
 * command is offered on every deactivated object, and a refusal of the server — whatever its status,
 * declared or not — is told as any other.
 *
 * Every prop is data — the kind of the object, its identifier, its version, its name —, never a
 * function: a server component — a simple table — hands it over as a client one — a dense grid —
 * does (défaut n° 12 de `typescript.md`). In a dense grid, the command is out of the order of
 * tabulation, the grid being one stop: Enter on its cell presses it (`CELL_COMMAND`).
 */
"use client";

import { RotateCcw } from "lucide-react";
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
  useTransition,
} from "react";

import { type ActivationTarget, reactivate } from "@/api/actions/reference";
import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { rejected } from "@/components/commands/rejection";
import { CELL_COMMAND } from "@/components/grid/grid-keyboard";
import { Button } from "@/components/ui/button";

import { ActiveState } from "./section";

export type { ActivationTarget } from "@/api/actions/reference";

/** The outcome of a reactivation, and the reading of the list it was asked from. */
interface Reported {
  readonly outcome: Outcome<unknown>;
  /** What the list read when the command was pressed (`readingOf`). */
  readonly reading: string;
}

/** Where a reactivation tells its refusal, and what the list reads now; none outside a list. */
const Report = createContext<
  { readonly report: (reported: Reported) => void; readonly reading: string } | undefined
>(undefined);

/** The cell a grid of the list keeps active, the one stop of its tabulation; none outside a grid. */
const ACTIVE_CELL = '[role="grid"] [tabindex="0"], [role="treegrid"] [tabindex="0"]';

/**
 * What a list reads of the address: the values of the parameters it reads, in their order — a sort
 * or a search of another list of the screen leaves it as it is.
 */
function readingOf(address: URLSearchParams, reads: readonly string[]): string {
  return reads.map((name) => `${name}=${address.get(name) ?? ""}`).join("&");
}

/**
 * A list whose objects may be reactivated, and the refusal of the last reactivation, told above it
 * until dismissed: a success after it does not take it away, and the focus goes back to the active
 * cell of the grid — or to the list, ringed — once it is. A refusal is told only on the reading it
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
  const [reported, setReported] = useState<Reported>();
  const reading = readingOf(useSearchParams(), reads);
  const list = useRef<HTMLDivElement>(null);
  const clear = useCallback(() => {
    setReported(undefined);
  }, []);
  const refocus = useCallback(() => {
    const cell = list.current?.querySelector<HTMLElement>(ACTIVE_CELL);
    (cell ?? list.current)?.focus();
  }, []);
  const value = useMemo(() => ({ report: setReported, reading }), [reading]);
  return (
    <div
      ref={list}
      tabIndex={-1}
      className="flex min-h-0 flex-col gap-2 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <OutcomeNotice
        outcome={reported?.reading === reading ? reported.outcome : undefined}
        onClear={clear}
        onDismissed={refocus}
        dismissible
      />
      <Report value={value}>{children}</Report>
    </div>
  );
}

/** The command that reactivates an object, named after it. */
export function ReactivateCommand({
  target,
  name,
}: {
  readonly target: ActivationTarget;
  /** The name of the object, as the list shows it. */
  readonly name: string;
}) {
  const t = useTranslations("reference.state");
  const list = useContext(Report);
  const [pending, startTransition] = useTransition();
  const run = () => {
    if (pending) {
      return;
    }
    // The reading the command is pressed on: its refusal is told on it alone.
    const reading = list?.reading ?? "";
    startTransition(async () => {
      const outcome = await reactivate(target).catch(rejected);
      // A success reads the page anew (`refresh`), and leaves a refusal before it told.
      if (outcome.kind !== "done") {
        list?.report({ outcome, reading });
      }
    });
  };
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      tabIndex={-1}
      {...{ [CELL_COMMAND]: "" }}
      aria-label={t("reactivate", { name })}
      aria-busy={pending}
      className="h-5 px-1.5 text-xs"
      onClick={run}
    >
      <RotateCcw aria-hidden="true" />
      {t("reactivateShort")}
    </Button>
  );
}

/**
 * The state of an object in a list: active, or deactivated — said by a mark and a word —, with the
 * command that reactivates it where the session may.
 */
export function StateCell({
  active,
  target,
  name,
  reactivable,
}: {
  readonly active: boolean;
  readonly target: ActivationTarget;
  readonly name: string;
  /** Whether the session may modify this part of the reference (`platformOffer`). */
  readonly reactivable: boolean;
}) {
  return (
    <span className="inline-flex items-center gap-1.5">
      <ActiveState active={active} />
      {!active && reactivable ? <ReactivateCommand target={target} name={name} /> : null}
    </span>
  );
}
