// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cards of the ends of the background tasks (WF-IHM-0080, US-2170): a user who went to another
 * screen while a treatment ran is told its end there, by a card floating in the corner of the
 * window, over the page — which it does not move, unlike a banner —, for each success and each
 * failure; a follow-up interrupted says nothing of the task, and has none. Mounted by the shell, fed
 * by the tracker, which keeps them (`Tracking.cards`).
 *
 * A card says the end as the log of the ends does, and the motive of a failure; it offers what
 * follows: « Télécharger » the file of an export — read anew first, as from the panel —, else
 * « Ouvrir » the screen the task was started from — the revisions after a marking, the screen where
 * a failed treatment is run again —; a task found again, its screen unknown, has its cross alone. A
 * file served once (WF-DAT-0120) is offered no more once it has gone: downloaded by itself, or read
 * anew and found gone, the card keeps its sentence and its cross alone; what the route refused when
 * the file was to download by itself, the card tells. It stays until it is opened — « Ouvrir » by a
 * plain click, not one that opens another tab —, or closed by its cross — no timer takes it away,
 * its action would be missed. The cards stack, the last on top, in a column bounded by the window,
 * which scrolls.
 *
 * Announced without taking the focus: by the log of the ends of the shell, which reads out the
 * same sentence as the card shows it — the cards themselves are no live region, which would read
 * each end twice. The end is noted in the history of the messages by that log too, which the panel
 * « Tâches et messages » keeps: a card closed is read again there. A card closed while the focus was
 * in it — by its cross, or opened — gives the focus to the next card, else the one before, else to
 * the button of the bar that opens the panel; its offer gone, to its own cross.
 */
"use client";

import { CircleAlert, CircleCheck, ExternalLink, X } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { type MouseEvent, useId, useRef, useState } from "react";

import type { Outcome } from "@/api/problem";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { useScreenName } from "@/components/notices/message-list";
import { Button, buttonVariants } from "@/components/ui/button";

import { DownloadResult } from "./result-download";
import { END_SENTENCE, Motive, useTaskName } from "./task-entry";
import { useEndCards, useTrackerDispatch } from "./task-tracker";
import { type EndCardLine, givesFile } from "./tracking";

/** What a card is given: its end, and how it is closed. */
interface EndCardProps {
  readonly line: EndCardLine;
  /** Hand the stack the cross of the card, to give it the focus. */
  readonly crossRef: (element: HTMLButtonElement | null) => void;
  /** Close the card: opened, or closed by its cross. */
  readonly onClose: () => void;
}

/** Whether a click is a plain one, which opens the link in place — not in another tab or window. */
function plainClick(event: MouseEvent): boolean {
  return event.button === 0 && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey;
}

/** What follows a card: the download of a file, or the screen the task was started from. */
function Follow({
  line,
  name,
  onOpened,
  onGone,
}: Omit<EndCardProps, "crossRef" | "onClose"> & {
  readonly name: string;
  readonly onOpened: () => void;
  /** The offer to download read anew and found gone, before it is taken away. */
  readonly onGone: () => void;
}) {
  const t = useTranslations();
  const dispatch = useTrackerDispatch();
  const screenName = useScreenName();
  const [refusal, setRefusal] = useState<Outcome<unknown>>();
  const [unavailable, setUnavailable] = useState(false);
  // The refusal of the download that left by itself, once dismissed.
  const [dismissed, setDismissed] = useState<Outcome<unknown>>();
  if (givesFile(line.task)) {
    const told = refusal ?? (line.refusal === dismissed ? undefined : line.refusal);
    return (
      <>
        {line.delivered === true || unavailable ? null : (
          <CommandTooltip label={t("tasks.cards.download")} help={t("commands.downloadEnd.help")}>
            <DownloadResult
              taskKey={line.key}
              task={line.task}
              name={name}
              label={t("tasks.cards.download")}
              dispatch={dispatch}
              onChecked={(outcome, left) => {
                if (left) {
                  onOpened();
                  return;
                }
                if (outcome.kind === "done") {
                  onGone();
                }
                setUnavailable(outcome.kind === "done");
                setRefusal(outcome.kind === "done" ? undefined : outcome);
              }}
            />
          </CommandTooltip>
        )}
        {unavailable ? (
          <p role="alert" className="basis-full text-destructive">
            {t("tasks.resultUnavailable")}
          </p>
        ) : null}
        <OutcomeNotice
          outcome={told}
          onClear={() => {
            setRefusal(undefined);
            setDismissed(line.refusal);
          }}
          subject={name}
        />
      </>
    );
  }
  const { from } = line;
  if (from === undefined) {
    return null;
  }
  return (
    <CommandTooltip label={t("tasks.cards.open")} help={t("commands.openEnd.help")}>
      <Link
        href={from.href}
        aria-label={t("tasks.cards.openLabel", { task: name, screen: screenName(from) })}
        className={buttonVariants({ variant: "outline", size: "sm" })}
        onClick={(event) => {
          if (plainClick(event)) {
            onOpened();
          }
        }}
      >
        <ExternalLink aria-hidden="true" />
        {t("tasks.cards.open")}
      </Link>
    </CommandTooltip>
  );
}

/** The card of one end: its sentence, the motive of a failure, what follows, and its cross. */
function EndCard({ line, crossRef, onClose }: EndCardProps) {
  const t = useTranslations();
  const name = useTaskName(line);
  const heading = useId();
  const failed = line.end === "failed";
  const Icon = failed ? CircleAlert : CircleCheck;
  const close = t("tasks.cards.close", { task: name });
  const group = useRef<HTMLDivElement>(null);
  const cross = useRef<HTMLButtonElement>(null);
  return (
    <div
      ref={group}
      role="group"
      aria-labelledby={heading}
      className="space-y-2 rounded-xl border bg-card p-3 text-sm text-card-foreground shadow-md"
    >
      <div className="flex items-start gap-2">
        <Icon
          aria-hidden="true"
          className={`mt-0.5 size-4 shrink-0 ${failed ? "text-destructive" : ""}`}
        />
        <p id={heading} className="flex-1 font-medium">
          {t(`tasks.${END_SENTENCE[line.end]}`, { task: name })}
        </p>
        <CommandTooltip label={close} help={t("commands.closeEnd.help")}>
          <Button
            ref={(element) => {
              cross.current = element;
              crossRef(element);
            }}
            type="button"
            variant="ghost"
            size="icon"
            aria-label={close}
            className="size-6"
            onClick={onClose}
          >
            <X aria-hidden="true" />
          </Button>
        </CommandTooltip>
      </div>
      {failed ? <Motive problem={line.problem} /> : null}
      <div className="flex flex-wrap justify-end gap-2">
        <Follow
          line={line}
          name={name}
          onOpened={onClose}
          onGone={() => {
            // The focus on the offer that goes stays in the card, on its cross.
            if (group.current?.contains(document.activeElement) === true) {
              cross.current?.focus();
            }
          }}
        />
      </div>
    </div>
  );
}

/** The stack of the cards of the ends, in the corner of the window; nothing while there is none. */
export function EndCards() {
  const t = useTranslations("tasks");
  const { cards, button } = useEndCards();
  const dispatch = useTrackerDispatch();
  const crosses = useRef(new Map<number, HTMLButtonElement>());
  const stack = useRef<HTMLElement>(null);
  if (cards.length === 0) {
    return null;
  }
  const close = (id: number) => {
    // The focus goes on when it was in the stack — or left on the page, the button that held it
    // gone —, never taken from where the user put it meanwhile, a download read anew at length.
    const focused = document.activeElement;
    if (
      focused === null ||
      focused === document.body ||
      stack.current?.contains(focused) === true
    ) {
      const index = cards.findIndex((card) => card.id === id);
      const neighbour = cards[index + 1] ?? cards[index - 1];
      const target = neighbour === undefined ? undefined : crosses.current.get(neighbour.id);
      (target ?? button.current)?.focus();
    }
    dispatch({ type: "card_closed", id });
  };
  return (
    <section
      ref={stack}
      aria-label={t("cards.label")}
      className="fixed right-4 bottom-4 z-40 max-h-[calc(100svh-2rem)] w-80 max-w-[calc(100vw-2rem)] overflow-y-auto p-1"
    >
      <ol className="space-y-2">
        {cards.map((line) => (
          <li key={line.id}>
            <EndCard
              line={line}
              crossRef={(element) => {
                if (element === null) {
                  crosses.current.delete(line.id);
                } else {
                  crosses.current.set(line.id, element);
                }
              }}
              onClose={() => {
                close(line.id);
              }}
            />
          </li>
        ))}
      </ol>
    </section>
  );
}
