// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A command of a screen (WF-IHM-0090): absent when the user may not exercise it; present and
 * available; or present and unavailable, naming each condition it lacks in a text everyone
 * reads — shown beside it, and the description of the button for a screen reader.
 *
 * An unavailable command stays in the order of the keyboard, marked `aria-disabled`, so that
 * its description is heard; pressing it does nothing. Greying it out is a convenience, not a
 * protection: an available command runs its server action, and the refusal the server may
 * still oppose is told like any outcome (`OutcomeNotice`).
 */
"use client";

import { useLocale, useTranslations } from "next-intl";
import { type ReactElement, type Ref, useId, useState, useTransition } from "react";

import type { Outcome } from "@/api/problem";
import { Button } from "@/components/ui/button";
import { formatLocale } from "@/i18n/format";

import { type CommandOffer, UNAVAILABLE, unmetId } from "./offer";
import { type ObjectNames, OutcomeNotice } from "./outcome-notice";

/** A command, what it is called, and what it does. */
export interface CommandProps {
  /** What the screen offers of the command; `undefined` when the user may not exercise it. */
  readonly offer: CommandOffer | undefined;
  readonly label: string;
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
  const t = useTranslations("commands");
  const conditionLabel = useTranslations("enums.CommandCondition");
  const locale = useLocale();
  if (id === undefined) {
    return null;
  }
  const missing = offer.missing_conditions.map((condition) => conditionLabel(condition));
  return (
    <p id={id} className="max-w-64 text-xs text-muted-foreground">
      {t("unmet", {
        count: missing.length,
        conditions: new Intl.ListFormat(formatLocale(locale), { type: "conjunction" }).format(
          missing,
        ),
      })}
    </p>
  );
}

/** Render a command as the screen offers it, and tell of the outcome of running it. */
export function Command({ offer, label, icon, action, names, disclosure }: CommandProps) {
  const id = useId();
  const [pending, startTransition] = useTransition();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  if (offer === undefined) {
    return null;
  }
  const unmet = unmetId(offer, id);
  const run = () => {
    if (!offer.is_available || pending) {
      return;
    }
    if (disclosure !== undefined) {
      disclosure.toggle();
      return;
    }
    if (action === undefined) {
      return;
    }
    startTransition(async () => {
      setOutcome(await action());
    });
  };
  return (
    <div className="space-y-1">
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-disabled={offer.is_available ? undefined : true}
        aria-describedby={unmet}
        aria-busy={pending}
        aria-expanded={disclosure?.expanded}
        aria-controls={disclosure?.expanded === true ? disclosure.controls : undefined}
        ref={disclosure?.ref}
        className={UNAVAILABLE}
        onClick={run}
      >
        {icon}
        {label}
      </Button>
      <UnmetConditions id={unmet} offer={offer} />
      <OutcomeNotice
        outcome={outcome}
        names={names}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
    </div>
  );
}
