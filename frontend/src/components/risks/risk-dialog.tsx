// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the commands of a risk that open a form share (US-0520, WF-IHM-0090): the dialog and what it
 * keeps of its openings (`useRiskDialog`), the command that opens it as its object lists it
 * (`OpensForm`) and the status that says the last write (`Status`). « Identifier un risque »,
 * « Modifier » and « Réexaminer » are made of them (`risk-commands.tsx`, `risk-review.tsx`).
 */
"use client";

import { type ReactElement, type Ref, useEffect, useId, useRef, useState } from "react";

import { Command } from "@/components/commands/command";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { type CommandOffer, UNAVAILABLE } from "@/components/commands/offer";
import { WritingNote } from "@/components/reference/reference-form";
import { Button } from "@/components/ui/button";

/**
 * The form a command opens, and what it keeps of its openings: how many there were, which is open,
 * whether a write is under way, and the control to give the focus back to once it has closed.
 */
export function useRiskDialog(kept?: {
  readonly writing: boolean;
  readonly setWriting: (writing: boolean) => void;
}) {
  const [open, setOpen] = useState<number>();
  const [ownWriting, setOwnWriting] = useState(false);
  // The state of the write is the caller's when it must outlive the dialog's screen.
  const writing = kept?.writing ?? ownWriting;
  const setWriting = kept?.setWriting ?? setOwnWriting;
  // How many times the form was opened: what tells an opening from the next.
  const openings = useRef(0);
  // The opening that is open, set as it opens and closes — never in an effect, which a late answer
  // would pass before.
  const current = useRef<number>(undefined);
  // Whether the screen the form was opened on is still shown, which a declaration answered leads from.
  const shown = useRef(true);
  const trigger = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    shown.current = true;
    return () => {
      shown.current = false;
    };
  }, []);
  return {
    open,
    writing,
    setWriting,
    trigger,
    shown,
    current,
    opening: () => {
      if (writing) {
        return;
      }
      openings.current += 1;
      current.current = openings.current;
      setOpen(openings.current);
    },
    close: () => {
      current.current = undefined;
      setOpen(undefined);
    },
  };
}

/**
 * A command that opens a form, as its object lists it: nothing when absent; the plain unavailable
 * command with the conditions it lacks; available, a button that opens, inactive and described by
 * « Enregistrement en cours… » while a write of the form is under way.
 */
export function OpensForm({
  offer,
  label,
  help,
  icon,
  writing,
  trigger,
  onOpen,
}: {
  readonly offer: CommandOffer | undefined;
  readonly label: string;
  /** What the command does, translated. */
  readonly help: string;
  readonly icon: ReactElement;
  readonly writing: boolean;
  readonly trigger: Ref<HTMLButtonElement>;
  readonly onOpen: () => void;
}) {
  const why = useId();
  if (offer === undefined) {
    return null;
  }
  if (!offer.is_available) {
    return <Command offer={offer} label={label} help={help} icon={icon} />;
  }
  return (
    <div className="space-y-1">
      <CommandTooltip label={label} help={help} describedBy={writing ? why : undefined}>
        <Button
          ref={trigger}
          type="button"
          variant="outline"
          size="sm"
          aria-disabled={writing ? true : undefined}
          aria-busy={writing}
          className={UNAVAILABLE}
          onClick={onOpen}
        >
          {icon}
          {label}
        </Button>
      </CommandTooltip>
      <WritingNote id={why} writing={writing} />
    </div>
  );
}

/** The status the last write of a command said, read out by a reader of the screen. */
export function Status({
  said,
}: {
  readonly said: { readonly text: string; readonly count: number } | undefined;
}) {
  return (
    <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
      {said === undefined ? null : <span key={said.count}>{said.text}</span>}
    </p>
  );
}
