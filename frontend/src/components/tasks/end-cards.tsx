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
 * a failed treatment is run again —; a task found again, its screen unknown, has its cross alone. It
 * stays until it is opened, or closed by its cross — no timer takes it away, its action would be
 * missed. The cards stack, the last on top, in a column bounded by the window, which scrolls.
 *
 * Announced without taking the focus: by the log of the ends of the shell, which reads out the
 * same sentence as the card shows it — the cards themselves are no live region, which would read
 * each end twice. The end is noted in the history of the messages by that log too, which the panel
 * « Tâches et messages » keeps: a card closed is read again there. A card closed from the keyboard
 * gives the focus to the next card, else the one before, else to the button of the bar that opens
 * the panel.
 */
"use client";

import { CircleAlert, CircleCheck, ExternalLink, X } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { useId, useRef, useState } from "react";

import type { Outcome } from "@/api/problem";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { useScreenName } from "@/components/notices/message-list";
import { Button, buttonVariants } from "@/components/ui/button";

import { DownloadResult } from "./result-download";
import { END_SENTENCE, Motive, useTaskName } from "./task-entry";
import { useEndCards, useTrackerDispatch } from "./task-tracker";
import { type EndLine, givesFile } from "./tracking";

/** What a card is given: its end, and how it is closed. */
interface EndCardProps {
  readonly line: EndLine;
  /** Hand the stack the cross of the card, to give it the focus. */
  readonly crossRef: (element: HTMLButtonElement | null) => void;
  /** Close the card; `focus`, when the focus is to go on — closed by its cross. */
  readonly onClose: (focus: boolean) => void;
}

/** What follows a card: the download of a file, or the screen the task was started from. */
function Follow({
  line,
  name,
  onOpened,
}: Omit<EndCardProps, "crossRef" | "onClose"> & {
  readonly name: string;
  readonly onOpened: () => void;
}) {
  const t = useTranslations();
  const dispatch = useTrackerDispatch();
  const screenName = useScreenName();
  const [refusal, setRefusal] = useState<Outcome<unknown>>();
  const [unavailable, setUnavailable] = useState(false);
  if (givesFile(line.task)) {
    return (
      <>
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
              setUnavailable(outcome.kind === "done");
              setRefusal(outcome.kind === "done" ? undefined : outcome);
            }}
          />
        </CommandTooltip>
        {unavailable ? (
          <p role="alert" className="basis-full text-destructive">
            {t("tasks.resultUnavailable")}
          </p>
        ) : null}
        <OutcomeNotice
          outcome={refusal}
          onClear={() => {
            setRefusal(undefined);
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
        onClick={onOpened}
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
  return (
    <div
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
            ref={crossRef}
            type="button"
            variant="ghost"
            size="icon"
            aria-label={close}
            className="size-6"
            onClick={() => {
              onClose(true);
            }}
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
          onOpened={() => {
            onClose(false);
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
  if (cards.length === 0) {
    return null;
  }
  const close = (id: number, focus: boolean) => {
    if (focus) {
      const index = cards.findIndex((card) => card.id === id);
      const neighbour = cards[index + 1] ?? cards[index - 1];
      const target = neighbour === undefined ? undefined : crosses.current.get(neighbour.id);
      (target ?? button.current)?.focus();
    }
    dispatch({ type: "card_closed", id });
  };
  return (
    <section
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
              onClose={(focus) => {
                close(line.id, focus);
              }}
            />
          </li>
        ))}
      </ol>
    </section>
  );
}
