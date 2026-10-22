// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The Kanban of the start of the tasks (FBS-4.5.3, WF-RAE-0030), as the contract gives it
 * (`listStartableTasks`, #425): a column of every task not started, whatever its predecessors —
 * WF-RAE-0030 does not make the start depend on them —, one of the tasks started, whose remaining
 * to commit is to re-estimate, and one of the tasks completed, which the Kanban reopens, each in
 * the order of the answer. A task is a card: its row number and its label; its finish, and the
 * mark of a finish past the date of calculation (`finish_overdue`), or, completed, the date it was
 * (`completed_on`); and, for a milestone not started whose predecessors are all completed, as the
 * API says (`predecessors_completed`), the mark that invites one to complete it, a text and an icon
 * (WF-IHM-0070), which nothing does by itself. A task is started or it is not: no percentage shows,
 * nor is entered (US-0230).
 *
 * A card is chosen by a click and makes, by its menu, the gestures its task lists
 * (`available_commands`, WF-IHM-0090): start, complete, reopen, or enter the remaining to commit,
 * which leads to the grid of the remaining to commit on that task. A task is started or completed on
 * a date the user enters, the day's by default. The answer of the API replaces the card in the
 * column of its new state, and the focus follows it; a refusal is told on the card. The screen
 * offers no gesture the card does not list, and deduces none of the nature of the task or of its
 * lines.
 */
"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { useEffect, useMemo, useRef, useState, useTransition } from "react";

import { setTaskProgress } from "@/api/actions/nodes";
import { useHeldCommand } from "@/components/commands/held";

import type { TaskProgress } from "./address";
import { type Asking, Card, type CardActions, DATED, type Notice } from "./kanban-card";
import {
  type CardGesture,
  cardOf,
  COLUMNS,
  type KanbanCard,
  type KanbanColumns,
  type KanbanStructure,
  replaced,
  TITLE,
} from "./kanban-cards";

/**
 * Render the Kanban of the start of the tasks: its three columns, each a list of cards, and the
 * gestures of the card chosen. The cards the API answered replace theirs until the screen reads
 * them anew (`replaced`).
 */
export function Kanban({
  columns,
  structure,
  remaining,
}: {
  readonly columns: KanbanColumns;
  readonly structure: KanbanStructure;
  /** The address of the grid of the remaining to commit of the revision. */
  readonly remaining: string;
}) {
  const t = useTranslations("kanban");
  const router = useRouter();
  const held = useHeldCommand();
  const [, startTransition] = useTransition();
  const [answered, setAnswered] = useState<Readonly<Record<string, KanbanCard>>>({});
  const [selected, setSelected] = useState<string>();
  const [writing, setWriting] = useState<string>();
  const [asking, setAsking] = useState<Asking>();
  const [notices, setNotices] = useState<Readonly<Record<string, Notice>>>({});
  const [announced, setAnnounced] = useState("");
  const [focusing, setFocusing] = useState<{ readonly id: string; readonly form: boolean }>();
  const elements = useRef(new Map<string, HTMLElement>());
  const date = useRef<HTMLInputElement | null>(null);
  // The card chosen now, set at the very moment it is: an answer judges against it (defect 2).
  const chosen = useRef<string>(undefined);
  const shown = useMemo(() => replaced(columns, answered), [columns, answered]);

  // The focus follows the card moved, which another column mounts anew, or the field of the date.
  useEffect(() => {
    if (focusing === undefined) {
      return;
    }
    (focusing.form ? date.current : elements.current.get(focusing.id))?.focus();
  }, [focusing]);

  const titleOf = (state: TaskProgress) => t(TITLE[state]);
  const say = (id: string, notice: Notice | undefined) => {
    setNotices((now) => {
      const rest = Object.entries(now).filter(([key]) => key !== id);
      return Object.fromEntries(notice === undefined ? rest : [...rest, [id, notice]]);
    });
  };

  /** Make a gesture the card lists, on the date given for the gestures that happen on one. */
  const write = (card: KanbanCard, gesture: CardGesture, occurredOn: string | undefined) => {
    const progress = gesture.progress;
    if (progress === null || writing !== undefined) {
      return;
    }
    setWriting(card.node_id);
    setAsking(undefined);
    setFocusing({ id: card.node_id, form: false });
    say(card.node_id, undefined);
    startTransition(async () => {
      const outcome = await held(
        setTaskProgress(structure, card.node_id, {
          progress,
          ...(occurredOn === undefined ? {} : { occurred_on: occurredOn }),
          lock_version: card.lock_version,
        }),
      );
      setWriting(undefined);
      // The user may have chosen another card while this one was written: the choice and the focus
      // stay where they went, never brought back to the card answered.
      const stays = chosen.current === card.node_id;
      if (stays) {
        setFocusing({ id: card.node_id, form: false });
      }
      if (outcome.kind !== "done") {
        say(card.node_id, { kind: "outcome", outcome });
        return;
      }
      const node = outcome.data.nodes.find((each) => each.node_id === card.node_id);
      const state = node?.task?.progress;
      if (node !== undefined && state !== undefined) {
        setAnswered((now) => ({ ...now, [card.node_id]: cardOf(node, state) }));
        setAnnounced(t("moved", { label: card.label, column: titleOf(state) }));
      }
      // The tasks are read anew either way: the card answered lists no gesture until they are.
      router.refresh();
    });
  };

  /** Ask a gesture of a card: its date first when it happens on one, else at once. */
  const gesture = (card: KanbanCard, asked: CardGesture) => {
    if (writing !== undefined) {
      return;
    }
    if (DATED.has(asked.command)) {
      setAsking({ id: card.node_id, gesture: asked });
      setFocusing({ id: card.node_id, form: true });
      return;
    }
    write(card, asked, undefined);
  };

  const actions: CardActions = {
    remaining,
    selected,
    writing,
    element: (id, element) => {
      if (element === null) {
        elements.current.delete(id);
      } else {
        elements.current.set(id, element);
      }
    },
    field: (element) => {
      date.current = element;
    },
    choose: (id) => {
      chosen.current = id;
      setSelected(id);
    },
    gesture,
    date: write,
    cancel: (id) => {
      setAsking(undefined);
      setFocusing({ id, form: false });
    },
    forget: (id) => {
      say(id, undefined);
      setFocusing({ id, form: false });
    },
  };

  return (
    <div className="space-y-3">
      <p role="status" className="sr-only">
        {announced}
      </p>
      <div className="grid gap-4 sm:grid-cols-3">
        {COLUMNS.map(([state, title]) => {
          const listed = shown[state];
          return (
            <section key={state} aria-label={t(title)} className="space-y-2 rounded-md">
              <h2 className="text-sm font-semibold">{t(title)}</h2>
              {listed.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t("empty")}</p>
              ) : (
                <ul className="space-y-2">
                  {listed.map((card) => (
                    <Card
                      key={card.node_id}
                      card={card}
                      actions={actions}
                      state={{
                        notice: notices[card.node_id],
                        asking: asking?.id === card.node_id ? asking : undefined,
                      }}
                    />
                  ))}
                </ul>
              )}
            </section>
          );
        })}
      </div>
    </div>
  );
}
