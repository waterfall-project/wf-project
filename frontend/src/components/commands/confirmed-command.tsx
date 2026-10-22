// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A command that asks for a confirmation before it runs (WF-IHM-0110): pressed available, it opens
 * a form in the page, which says what the command does — a sentence that describes the button that
 * confirms —, and what it asks besides, if anything. Confirmed, a server action asks the API, which
 * judges it; what the API answered stays said under the command — what was done, in a status, or
 * the refusal (`OutcomeNotice`), which names the condition that lacks. The form closes once the
 * command is done, the focus back on the command; a refusal leaves it open, with its sentence.
 *
 * The form is part of the page, not a dialog: nothing else of the screen is withheld while it is
 * open. The confirmation is the same for the abandon of a revision, the designation of the
 * reference and the update of the rates: they differ by the sentence, the action and what follows.
 */
"use client";

import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  type ReactElement,
  type ReactNode,
  type SubmitEvent,
  useEffect,
  useId,
  useRef,
  useState,
  useTransition,
} from "react";

import type { Outcome } from "@/api/problem";
import { DoneNotice } from "@/components/notices/done-notice";
import { Button } from "@/components/ui/button";

import { Command } from "./command";
import { useHeldCommand } from "./held";
import type { CommandOffer } from "./offer";
import { type ObjectNames, OutcomeNotice } from "./outcome-notice";

/** A command, what it asks to be confirmed, and what follows it. */
export interface ConfirmedCommandProps<T> {
  readonly offer: CommandOffer;
  readonly label: string;
  /** The icon before its name (`commandIcon`). */
  readonly icon: ReactElement;
  /** What the command does, which describes the button that confirms. */
  readonly statement: string;
  readonly submit: string;
  /** Whether the command is presented at all: not, and only what was told of it stays. */
  readonly presented?: boolean | undefined;
  /** Whether the confirmation may be given: what the form asks besides is entered. */
  readonly ready?: boolean | undefined;
  /** What the form asks besides, between the statement and the buttons. */
  readonly children?: ReactNode;
  readonly names: ObjectNames;
  /** What the command is about, by its name, which the history of the messages notes. */
  readonly subject: string | undefined;
  /** The server action. */
  readonly run: () => Promise<Outcome<T>>;
  /** What is said once it is done. */
  readonly done: (data: T) => string;
  /** What follows once it is done, besides what is said. */
  readonly onDone?: ((data: T) => void) | undefined;
}

const UNAVAILABLE = "aria-disabled:cursor-not-allowed aria-disabled:opacity-50";

/** Offer a command, open its confirmation when pressed, and say what followed. */
export function ConfirmedCommand<T>({
  offer,
  label,
  icon,
  statement,
  submit,
  presented = true,
  ready = true,
  children,
  names,
  subject,
  run,
  done,
  onDone,
}: ConfirmedCommandProps<T>) {
  const t = useTranslations("revisionCommands");
  const form = useId();
  const sentence = `${form}-statement`;
  const held = useHeldCommand();
  const [open, setOpen] = useState(false);
  // What was told is kept as it was told: the page read again may change what `done` would say.
  const [result, setResult] = useState<{ readonly data: T; readonly title: string }>();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const button = useRef<HTMLButtonElement>(null);
  // The page read again may no longer offer the command: its confirmation is not shown.
  const offered = presented && offer.is_available;
  const shown = open && offered;
  useEffect(() => {
    if (!shown) {
      return undefined;
    }
    const command = button.current;
    // Once the confirmation is shown no more, whatever the reason: when the page read again does
    // not offer the command any more, it is closed and does not come back with the command, and
    // the focus the form held, fallen on the page, goes back to the command if it is still there.
    return () => {
      setOpen(false);
      if (document.activeElement === document.body || document.activeElement === null) {
        command?.focus();
      }
    };
  }, [shown]);
  const close = () => {
    setOpen(false);
    button.current?.focus();
  };

  const confirm = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending || !ready) {
      return;
    }
    startTransition(async () => {
      const answer = await held(run());
      if (answer.kind === "done") {
        setResult({ data: answer.data, title: done(answer.data) });
        setOutcome(undefined);
        close();
        onDone?.(answer.data);
      } else {
        setOutcome(answer);
      }
    });
  };

  return (
    <div className="space-y-2">
      {presented ? (
        <Command
          offer={offer}
          label={label}
          icon={icon}
          names={names}
          subject={subject}
          disclosure={{
            expanded: shown,
            controls: form,
            toggle: () => {
              if (!open) {
                setOutcome(undefined);
              }
              setOpen(!open);
            },
            ref: button,
          }}
        />
      ) : null}
      {shown ? (
        <form
          id={form}
          aria-label={label}
          aria-busy={pending}
          onSubmit={confirm}
          className="max-w-xl space-y-2 rounded-md border p-3 text-sm"
        >
          <p id={sentence}>{statement}</p>
          {children}
          <div className="flex gap-2">
            <Button
              type="submit"
              size="sm"
              aria-describedby={sentence}
              aria-disabled={ready ? undefined : true}
              className={UNAVAILABLE}
            >
              {icon}
              {submit}
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              aria-disabled={pending ? true : undefined}
              className={UNAVAILABLE}
              onClick={() => {
                if (!pending) {
                  close();
                }
              }}
            >
              <X aria-hidden="true" />
              {t("cancel")}
            </Button>
          </div>
          <OutcomeNotice
            outcome={outcome}
            names={names}
            subject={subject}
            onClear={() => {
              setOutcome(undefined);
            }}
          />
        </form>
      ) : null}
      <DoneNotice subject={subject} title={result?.title} of={result} />
    </div>
  );
}
