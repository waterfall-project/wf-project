// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A command of a screen (WF-IHM-0090): absent when the user may not exercise it; present and
 * available; or present and unavailable, naming each condition it lacks. The condition is read in
 * its tooltip, which opens on the pointer as on the focus of the keyboard, and in the region of the
 * refusals when the command is pressed (#3090); it is not written under the button. It is also the
 * description of the button for a screen reader, in a text hidden for that alone.
 *
 * An unavailable command stays in the order of the keyboard, marked `aria-disabled`, so that
 * its tooltip and its description are reached; pressing it runs nothing, and tells what it lacks
 * in an alert, which is the refusal the screen would have had from the server. Greying it out is a
 * convenience, not a protection: an available command runs its server action, and the refusal
 * the server may still oppose is told like any outcome (`OutcomeNotice`). The navigations of the
 * page wait for its outcome, and do not take place when it is refused (`useHeldCommand`, #688).
 *
 * Pressed, it waits for what it started — its server action, a write the command opened, the
 * background task it handed to the tracker — inert and saying so, the same way for every command
 * (`waiting.tsx`, #3103): a second press runs nothing, and an answer, a failure included, gives it
 * back — but a write whose connection was lost once sent, which gives it back once the screen has
 * been read anew (`useReadAnew`, US-2240).
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { CircleAlert } from "lucide-react";
import { type ReactElement, type Ref, useId, useState } from "react";

import type { Outcome } from "@/api/problem";
import type { PrincipalVariant } from "@/components/shell/section-card";
import { Button } from "@/components/ui/button";
import { formatLocale } from "@/i18n/format";

import { CommandTooltip } from "./command-tooltip";
import { useHeldCommand } from "./held";
import { type CommandOffer, UNAVAILABLE, unmetId } from "./offer";
import { type ObjectNames, OutcomeNotice, useReadAnew } from "./outcome-notice";
import { WaitingIcon, waitingAttributes } from "./waiting";
import { WritingNote } from "./writing-note";

/** A command, what it is called, and what it does. */
export interface CommandProps {
  /** What the screen offers of the command; `undefined` when the user may not exercise it. */
  readonly offer: CommandOffer | undefined;
  readonly label: string;
  /** What the command does, translated (`commands.<command>.help`): its tooltip says it. */
  readonly help: string;
  /**
   * The icon before its name, hidden from a screen reader (`commandIcon`): an element, which a
   * server component hands over as it hands over any child — a component would not cross.
   */
  readonly icon: ReactElement;
  /**
   * The server action the command runs. A command whose operation is still to be wired does
   * nothing when pressed.
   */
  readonly action?: (() => Promise<Outcome<unknown>>) | undefined;
  /** The names of the objects the screen shows, which name the object of a conflict. */
  readonly names?: ObjectNames | undefined;
  /**
   * What the command opens rather than running at once — the form of what it asks, a version
   * name —, in place of an action: pressed available, it opens or closes it.
   */
  readonly disclosure?: Disclosure | undefined;
  /** What the command is about, by its name, which the history of the messages notes. */
  readonly subject?: string | undefined;
  /**
   * Whether a write the command opened is under way: the command is then inactive, `aria-busy` and
   * described by the sentence of the write, so that a late answer cannot close a reopening (n° 24).
   */
  readonly writing?: boolean | undefined;
  /**
   * Whether the background task the command started still runs (`useTaskRunning`) — or, the command
   * mounted anew, the one of its aim it finds running (`useRunningTask`, #3404): the command waits
   * until it ends, and a failure gives it back, to run the same treatment again (WF-IHM-0080).
   */
  readonly running?: boolean | undefined;
  /**
   * The variant of its button: outlined, unless the command is the principal one of a card, which
   * gives it the variant of what it does (`SectionCard`, `principalVariant`).
   */
  readonly variant?: PrincipalVariant | undefined;
}

/**
 * The variant of the button of a command: outlined, unless its card gives it another. Kept out of
 * `Command`: a default (`variant = "outline"`, or `??`) there would bring its complexity over the
 * limit (15 for 14).
 */
function outlinedUnless(variant: PrincipalVariant | undefined): PrincipalVariant {
  return variant ?? "outline";
}

/** A command that opens what it asks before it runs. */
export interface Disclosure {
  readonly expanded: boolean;
  /** The identifier of what it opens. */
  readonly controls: string;
  readonly toggle: () => void;
  /** The button, which takes the focus back once what it opened has closed. */
  readonly ref?: Ref<HTMLButtonElement> | undefined;
}

/**
 * The text that names each condition an unavailable command lacks, shown beside it and the
 * description of its button (`unmetId`); nothing when it lacks none.
 */
export function UnmetConditions({
  id,
  offer,
}: {
  readonly id: string | undefined;
  readonly offer: CommandOffer;
}) {
  const unmet = useUnmet();
  if (id === undefined) {
    return null;
  }
  return (
    <p id={id} className="max-w-64 text-xs text-muted-foreground">
      {unmet(offer)}
    </p>
  );
}

/**
 * The text that names each condition an unavailable command lacks, hidden: it describes the button
 * (`unmetId`) for a screen reader, and the tooltip says it to everyone else (WF-IHM-0090).
 */
function HiddenUnmet({
  id,
  offer,
}: {
  readonly id: string | undefined;
  readonly offer: CommandOffer;
}) {
  const unmet = useUnmet();
  return id === undefined ? null : (
    <p id={id} hidden>
      {unmet(offer)}
    </p>
  );
}

/**
 * The refusal an unavailable command pressed tells, in the region of the refusals: what it lacks.
 * It belongs to the press: the caller keys it by the availability of the command, so that it is
 * mounted anew, and tells nothing, each time the command changes; it tells once a press has been
 * counted since it was mounted, and so does not come back, unavailable again, without a new press.
 */
function UnmetRefusal({
  offer,
  presses,
  unmet,
}: {
  readonly offer: CommandOffer;
  /** The presses of the command while unavailable. */
  readonly presses: number;
  /** The identifier of the conditions it lacks (`unmetId`): none when it lacks none. */
  readonly unmet: string | undefined;
}) {
  const text = useUnmet();
  const [seen] = useState(presses);
  if (presses === seen || unmet === undefined) {
    return null;
  }
  return (
    <div role="alert" className="flex max-w-64 items-start gap-1.5 text-xs text-destructive">
      <CircleAlert aria-hidden="true" className="mt-0.5 size-3.5 shrink-0" />
      <p>{text(offer)}</p>
    </div>
  );
}

/**
 * The refusal of the presses of a command a screen draws itself, unavailable: what it lacks, said
 * in the region of the refusals each time it is pressed (#3289). The screen counts the presses
 * while the command is unavailable (`presses`); the refusal forgets them when the command changes.
 */
export function PressRefusal({
  offer,
  presses,
}: {
  readonly offer: CommandOffer;
  readonly presses: number;
}) {
  return (
    <UnmetRefusal
      key={String(offer.is_available)}
      offer={offer}
      presses={presses}
      unmet={unmetId(offer, "press")}
    />
  );
}

/**
 * The sentence that names the conditions an unavailable command lacks, each by its label in the
 * language of the reader: the one sentence of every command a screen presents unavailable.
 */
export function useUnmet(): (offer: CommandOffer) => string {
  const t = useTranslations("commands");
  const conditionLabel = useTranslations("enums.CommandCondition");
  const locale = useLocale();
  return (offer) => {
    const missing = offer.missing_conditions.map((condition) => conditionLabel(condition));
    return t("unmet", {
      count: missing.length,
      conditions: new Intl.ListFormat(formatLocale(locale), { type: "conjunction" }).format(
        missing,
      ),
    });
  };
}

/**
 * What describes a command: the note of the write under way (`why`), while it is, and the unmet
 * condition, when it lacks one — both when both are said.
 */
function descriptionOf(
  writing: boolean,
  why: string,
  unmet: string | undefined,
): string | undefined {
  return writing ? [why, unmet].filter((part) => part !== undefined).join(" ") : unmet;
}

/** Render a command as the screen offers it, and tell of the outcome of running it. */
export function Command({
  offer,
  label,
  help,
  icon,
  action,
  names,
  disclosure,
  subject,
  writing = false,
  running = false,
  variant,
}: CommandProps) {
  const id = useId();
  const unmetText = useUnmet();
  // Busy from the press to the answer, and lifted in the very update that tells it — not a transition,
  // whose end would wait for every other async action of the page (#1484).
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  // An unavailable command pressed: it tells what it lacks, as the refusal it would have drawn.
  const [presses, setPresses] = useState(0);
  const held = useHeldCommand();
  // A write lost once sent: the command waits until the screen has been read anew (US-2240).
  const reading = useReadAnew(outcome);
  if (offer === undefined) {
    return null;
  }
  const unmet = unmetId(offer, id);
  const why = `${id}-writing`;
  const waiting = busy || writing || running || reading;
  const describedBy = descriptionOf(writing, why, unmet);
  const run = () => {
    if (!offer.is_available) {
      setPresses((count) => count + 1);
      return;
    }
    if (waiting) {
      return;
    }
    if (disclosure !== undefined) {
      disclosure.toggle();
      return;
    }
    if (action === undefined) {
      return;
    }
    setBusy(true);
    void held(action()).then((outcome) => {
      setOutcome(outcome);
      setBusy(false);
    });
  };
  return (
    <div className="space-y-1">
      <CommandTooltip
        label={label}
        help={help}
        unavailable={unmet === undefined ? undefined : unmetText(offer)}
        describedBy={describedBy}
      >
        <Button
          type="button"
          variant={outlinedUnless(variant)}
          size="sm"
          {...waitingAttributes(waiting)}
          // Unavailable with no condition to name: marked all the same, the tooltip saying none.
          {...(!offer.is_available && unmet === undefined ? { "aria-disabled": true } : {})}
          aria-expanded={disclosure?.expanded}
          aria-controls={disclosure?.expanded === true ? disclosure.controls : undefined}
          ref={disclosure?.ref}
          className={UNAVAILABLE}
          onClick={run}
        >
          <WaitingIcon waiting={waiting} icon={icon} />
          {label}
        </Button>
      </CommandTooltip>
      <HiddenUnmet id={unmet} offer={offer} />
      <PressRefusal offer={offer} presses={presses} />
      <WritingNote id={why} writing={writing} />
      <OutcomeNotice
        outcome={outcome}
        names={names}
        onClear={() => {
          setOutcome(undefined);
        }}
        subject={subject}
        reading={reading}
      />
    </div>
  );
}
