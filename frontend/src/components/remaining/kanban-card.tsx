// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A card of the Kanban and what it carries: its date, its menu of gestures, the date asked of an
 * event, what is told on it. The board (`kanban.tsx`) chooses, moves and writes; the card shows
 * and hands back what the user asked of it.
 */
"use client";

import {
  CalendarX2,
  CircleCheck,
  Diamond,
  Ellipsis,
  Flag,
  LoaderCircle,
  type LucideIcon,
  PenLine,
  Play,
  Undo2,
} from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useId, useRef, useState } from "react";

import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { useUnmet } from "@/components/commands/command";
import { UNAVAILABLE } from "@/components/commands/offer";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatPlanningDate } from "@/i18n/format";

import { type CardGesture, type KanbanCard, remainingHref } from "./kanban-cards";

type KanbanCommand = components["schemas"]["KanbanCommand"];

/** The icon of each gesture, before its name in the menu. */
const ICONS: Readonly<Record<KanbanCommand, LucideIcon>> = {
  start: Play,
  complete: CircleCheck,
  reopen: Undo2,
  enter_remaining: PenLine,
};

/** The type of the data a card carries when dragged: no text a field would take on a drop. */
const DRAG_TYPE = "application/x-waterfall-card";

/** What a card tells of the last gesture asked of it: the refusal of the API, or a sentence. */
export type Notice =
  | { readonly kind: "outcome"; readonly outcome: Outcome<unknown> }
  | { readonly kind: "said"; readonly sentence: string };

/** A gesture that waits for the date of its event, on the card it was asked of. */
export interface Asking {
  readonly id: string;
  readonly gesture: CardGesture;
}

/** The day, as a date of the planning, in the time of the workstation: what the date proposes. */
function today(): string {
  const now = new Date();
  const two = (value: number) => value.toString().padStart(2, "0");
  return `${now.getFullYear().toString()}-${two(now.getMonth() + 1)}-${two(now.getDate())}`;
}

/**
 * When a task of the Kanban ends: the date it was completed, or its finish, marked when it is past
 * the date of calculation, as the API says.
 */
function CardDate({ card }: { readonly card: KanbanCard }) {
  const t = useTranslations("kanban");
  const locale = useLocale();
  if (card.completed_on !== undefined) {
    return (
      <p className="text-xs text-muted-foreground">
        {t("completedOn", { date: formatPlanningDate(card.completed_on, locale, "short") })}
      </p>
    );
  }
  if (card.finish === undefined) {
    return null;
  }
  return (
    <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
      {t("finish", { date: formatPlanningDate(card.finish, locale, "short") })}
      {card.finish_overdue ? (
        <CalendarX2 role="img" aria-label={t("finishOverdue")} className="size-3.5">
          <title>{t("finishOverdue")}</title>
        </CalendarX2>
      ) : null}
    </p>
  );
}

/**
 * The menu of the gestures of a card: every gesture it lists, available or not — an unavailable one
 * stays in the menu, and names what it lacks (WF-IHM-0090) —, the entry of the remaining to commit a
 * link to the grid on the task. The focus goes where the gesture sends it, not back to the button.
 * The card opens it too with Enter, Space or the menu key.
 */
function CardMenu({
  card,
  remaining,
  busy,
  open,
  onOpenChange,
  onGesture,
  onDismiss,
}: {
  readonly card: KanbanCard;
  readonly remaining: string;
  readonly busy: boolean;
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly onGesture: (gesture: CardGesture) => void;
  /** The menu closed with no gesture chosen: the focus goes back to the card. */
  readonly onDismiss: () => void;
}) {
  const t = useTranslations("kanban");
  const commands = useTranslations("enums.KanbanCommand");
  const unmet = useUnmet();
  const chosen = useRef<CardGesture>(undefined);
  // Whether the menu was left by a click or a touch outside it: the focus then stays where it went.
  const outside = useRef(false);
  return (
    <DropdownMenu open={open} onOpenChange={onOpenChange}>
      <DropdownMenuTrigger asChild>
        <Button
          type="button"
          variant="outline"
          size="sm"
          aria-label={t("gestures", { label: card.label })}
          aria-busy={busy}
          className="h-7"
        >
          <Ellipsis aria-hidden="true" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="start"
        aria-label={t("gestures", { label: card.label })}
        onInteractOutside={() => {
          outside.current = true;
        }}
        onCloseAutoFocus={(event) => {
          const left = outside.current;
          outside.current = false;
          // The gesture waits for the menu to be gone: its focus trap would pull the focus back.
          const gesture = chosen.current;
          if (gesture !== undefined) {
            chosen.current = undefined;
            event.preventDefault();
            onGesture(gesture);
            return;
          }
          // Closed from the keyboard with no gesture: the focus goes back to the card, not to the
          // button of the menu, so that the arrows go on from it. Left by an interaction outside,
          // the guard of Radix keeps the focus where the user put it.
          if (!left) {
            event.preventDefault();
            onDismiss();
          }
        }}
      >
        {card.commands.map((gesture) => {
          const Icon = ICONS[gesture.command];
          const name = commands(gesture.command);
          const lacking = gesture.is_available ? null : (
            <span className="block text-xs text-muted-foreground">{unmet(gesture)}</span>
          );
          const label = (
            <>
              <Icon aria-hidden="true" />
              <span>
                {name}
                {lacking}
              </span>
            </>
          );
          if (!gesture.is_available) {
            return (
              <DropdownMenuItem
                key={gesture.command}
                aria-disabled="true"
                className={UNAVAILABLE}
                onSelect={(event) => {
                  event.preventDefault();
                }}
              >
                {label}
              </DropdownMenuItem>
            );
          }
          if (gesture.command === "enter_remaining") {
            return (
              <DropdownMenuItem key={gesture.command} asChild>
                <Link href={remainingHref(remaining, card)}>{label}</Link>
              </DropdownMenuItem>
            );
          }
          return (
            <DropdownMenuItem
              key={gesture.command}
              aria-disabled={busy ? "true" : undefined}
              className={UNAVAILABLE}
              onSelect={(event) => {
                if (busy) {
                  event.preventDefault();
                  return;
                }
                chosen.current = gesture;
              }}
            >
              {label}
            </DropdownMenuItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/** The date of the event of a gesture, asked on the card: the day's by default, a field of its own. */
function EventDate({
  gesture,
  onSubmit,
  onCancel,
  field,
}: {
  readonly gesture: CardGesture;
  readonly onSubmit: (date: string) => void;
  readonly onCancel: () => void;
  readonly field: (element: HTMLInputElement | null) => void;
}) {
  const t = useTranslations("kanban");
  const command = useTranslations("enums.KanbanCommand")(gesture.command);
  const id = useId();
  const [date, setDate] = useState(today);
  const [missing, setMissing] = useState(false);
  return (
    <form
      className="space-y-1.5"
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        if (date === "") {
          setMissing(true);
          return;
        }
        onSubmit(date);
      }}
      onKeyDown={(event) => {
        if (event.key === "Escape") {
          event.preventDefault();
          event.stopPropagation();
          onCancel();
        }
      }}
    >
      <Label htmlFor={id}>{t("eventDate")}</Label>
      <Input
        id={id}
        ref={field}
        type="date"
        value={date}
        aria-invalid={missing}
        aria-describedby={missing ? `${id}-missing` : undefined}
        onChange={(event) => {
          setDate(event.target.value);
          setMissing(false);
        }}
      />
      {missing ? (
        <p id={`${id}-missing`} role="alert" className="text-xs text-destructive">
          {t("dateRequired")}
        </p>
      ) : null}
      <div className="flex gap-2">
        <Button type="submit" size="sm">
          {command}
        </Button>
        <Button type="button" variant="ghost" size="sm" onClick={onCancel}>
          {t("cancel")}
        </Button>
      </div>
    </form>
  );
}

/** What the board hands a card: what is chosen, asked, told, and the gestures it makes. */
export interface CardActions {
  readonly remaining: string;
  /** The identifier of the help of the board, which every card is described by. */
  readonly hint: string;
  readonly selected: string | undefined;
  readonly tabStop: string | undefined;
  readonly dragged: string | undefined;
  readonly writing: string | undefined;
  readonly element: (id: string, element: HTMLElement | null) => void;
  readonly field: (element: HTMLInputElement | null) => void;
  readonly choose: (id: string) => void;
  readonly focusFrom: (id: string, key: string) => boolean;
  /** Carry the card to the column a sideways arrow leads to; whether the key was one. */
  readonly carryFrom: (card: KanbanCard, key: string) => boolean;
  readonly drag: (id: string | undefined) => void;
  readonly gesture: (card: KanbanCard, gesture: CardGesture) => void;
  readonly date: (card: KanbanCard, gesture: CardGesture, date: string) => void;
  readonly cancel: (id: string) => void;
  readonly forget: (id: string) => void;
  /** Read the tasks anew, after a reading that did not bring the card answered. */
  readonly retry: () => void;
}

/** What is asked or told on one card. */
export interface CardState {
  readonly asking: Asking | undefined;
  readonly notice: Notice | undefined;
  /** The card answered a gesture: being updated, or not up to date once the reading is over. */
  readonly reading: "updating" | "outdated" | undefined;
}

/** The title of a card: its number, the mark of a milestone, its label, and when it ends. */
function CardTitle({ card }: { readonly card: KanbanCard }) {
  const t = useTranslations("kanban");
  const due = card.is_milestone && card.state === "not_started" && card.predecessors_completed;
  return (
    <>
      <p className="flex items-baseline gap-2">
        <span className="tabular-nums text-muted-foreground">{card.row_number}</span>
        {card.is_milestone ? (
          <Diamond role="img" aria-label={t("milestone")} className="size-3.5 shrink-0">
            <title>{t("milestone")}</title>
          </Diamond>
        ) : null}
        <span className="font-medium">{card.label}</span>
      </p>
      <CardDate card={card} />
      {due ? (
        <p className="flex items-center gap-1.5 text-xs font-medium">
          <Flag aria-hidden="true" className="size-3.5 shrink-0" />
          {t("milestoneDue")}
        </p>
      ) : null}
    </>
  );
}

/** The mark of a card answered: the tasks are being read anew, or that reading did not reach it. */
function CardReading({
  reading,
  retry,
}: {
  readonly reading: CardState["reading"];
  readonly retry: () => void;
}) {
  const t = useTranslations("kanban");
  if (reading === "updating") {
    return (
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <LoaderCircle
          aria-hidden="true"
          className="size-3.5 animate-spin motion-reduce:animate-none"
        />
        {t("updating")}
      </p>
    );
  }
  if (reading === "outdated") {
    return (
      <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
        {t("outdated")}
        <Button
          type="button"
          variant="outline"
          size="sm"
          className="h-6 px-2 text-xs"
          onClick={retry}
        >
          {t("retry")}
        </Button>
      </p>
    );
  }
  return null;
}

/** What the card asks or tells besides its title: the date of the event asked, or a refusal. */
function CardAsks({
  card,
  actions,
  state: { asking, notice, reading },
}: {
  readonly card: KanbanCard;
  readonly actions: CardActions;
  readonly state: CardState;
}) {
  return (
    <>
      <CardReading reading={reading} retry={actions.retry} />
      {asking === undefined ? null : (
        <EventDate
          gesture={asking.gesture}
          field={actions.field}
          onSubmit={(date) => {
            actions.date(card, asking.gesture, date);
          }}
          onCancel={() => {
            actions.cancel(card.node_id);
          }}
        />
      )}
      {notice?.kind === "said" ? (
        <p role="alert" className="text-xs text-destructive">
          {notice.sentence}
        </p>
      ) : null}
      {notice?.kind === "outcome" ? (
        <OutcomeNotice
          outcome={notice.outcome}
          subject={card.label}
          dismissible
          onClear={() => {
            actions.forget(card.node_id);
          }}
        />
      ) : null}
    </>
  );
}

/** Whether a card is dragged: it lists a gesture that sends a state, and nothing is under way. */
function isDraggable(card: KanbanCard, writing: string | undefined, asked: boolean): boolean {
  return (
    writing === undefined && !asked && card.commands.some((gesture) => gesture.progress !== null)
  );
}

/** A card of the Kanban: a task, and whether it is a milestone to complete, as the API says. */
export function Card({
  card,
  actions,
  state,
}: {
  readonly card: KanbanCard;
  readonly actions: CardActions;
  readonly state: CardState;
}) {
  const { selected, dragged, writing } = actions;
  const isSelected = selected === card.node_id;
  const [menuOpen, setMenuOpen] = useState(false);
  const item = useRef<HTMLLIElement | null>(null);
  return (
    <li
      ref={(element) => {
        item.current = element;
        actions.element(card.node_id, element);
      }}
      tabIndex={actions.tabStop === card.node_id ? 0 : -1}
      aria-current={isSelected ? "true" : undefined}
      aria-describedby={actions.hint}
      aria-busy={writing === card.node_id}
      draggable={isDraggable(card, writing, state.asking !== undefined)}
      onFocus={(event) => {
        if (event.target === event.currentTarget) {
          actions.choose(card.node_id);
        }
      }}
      onKeyDown={(event) => {
        const opens =
          event.key === "Enter" ||
          event.key === " " ||
          event.key === "ContextMenu" ||
          (event.key === "F10" && event.shiftKey);
        if (
          event.target !== event.currentTarget ||
          event.ctrlKey ||
          event.altKey ||
          event.metaKey
        ) {
          return;
        }
        const handled = event.shiftKey
          ? actions.carryFrom(card, event.key)
          : actions.focusFrom(card.node_id, event.key);
        if (handled) {
          event.preventDefault();
          return;
        }
        if (opens && card.commands.length > 0) {
          event.preventDefault();
          setMenuOpen(true);
        }
      }}
      onDragStart={(event) => {
        // A type of its own: the identifier is no text a field where the card is dropped may take.
        // Firefox starts no drag without data set.
        event.dataTransfer.setData(DRAG_TYPE, card.node_id);
        event.dataTransfer.effectAllowed = "move";
        actions.choose(card.node_id);
        actions.drag(card.node_id);
      }}
      onDragEnd={() => {
        actions.drag(undefined);
      }}
      className={`space-y-1 rounded-md border bg-card p-2 text-sm outline-none focus-visible:ring-2 focus-visible:ring-ring ${
        isSelected ? "border-primary ring-1 ring-primary" : ""
      } ${dragged === card.node_id ? "opacity-50" : ""}`}
    >
      <CardTitle card={card} />
      {isSelected && card.commands.length > 0 ? (
        <div>
          <CardMenu
            card={card}
            remaining={actions.remaining}
            busy={writing !== undefined}
            open={menuOpen}
            onOpenChange={setMenuOpen}
            onDismiss={() => {
              item.current?.focus();
            }}
            onGesture={(gesture) => {
              actions.gesture(card, gesture);
            }}
          />
        </div>
      ) : null}
      <CardAsks card={card} actions={actions} state={state} />
    </li>
  );
}
