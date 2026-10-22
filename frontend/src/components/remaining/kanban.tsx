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
 * A card is chosen — by a click, by the arrows from card to card and from column to column — and
 * makes the gestures its task lists (`available_commands`, WF-IHM-0090): start, complete, reopen,
 * or enter the remaining to commit, which leads to the grid of the remaining to commit on that task.
 * It makes them by dragging it to a column, by its menu, or at the keyboard — Shift and the right or
 * left arrow carry it to the neighbouring column, the equivalent of the drag (WF-IHM-0100). A task
 * is started or completed on a date the user enters, the day's by default. The answer of the API
 * replaces the card in the column of its new state, and the focus follows it; a refusal is told on
 * the card, and the gesture a card does not list to a column is told on it too. The card moved says
 * it is being updated while the tasks are read anew, and that it is not up to date, with a way to
 * read them again, when that reading is over without having brought its answer (the principle of
 * the busy state of the grids, #1224). The screen offers no
 * gesture the card does not list, and deduces none of the nature of the task or of its lines.
 */
"use client";

import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  type DragEvent,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  useTransition,
} from "react";

import { setTaskProgress } from "@/api/actions/nodes";
import { useUnmet } from "@/components/commands/command";
import { useHeldCommand } from "@/components/commands/held";

import type { TaskProgress } from "./address";
import { AnsweredCards } from "./kanban-answers";
import { type Asking, Card, type CardActions, type CardState, type Notice } from "./kanban-card";
import {
  type CardGesture,
  cardOf,
  carriedTo,
  COLUMNS,
  DATED,
  focusOf,
  gestureToward,
  type KanbanCard,
  type KanbanColumns,
  type KanbanStructure,
  replaced,
  TITLE,
} from "./kanban-cards";

/** The mark of a card: updating while the tasks are read anew, outdated if that reading failed. */
function readingOf(answer: KanbanCard | undefined, failed: boolean): CardState["reading"] {
  if (answer === undefined) {
    return undefined;
  }
  return failed ? "outdated" : "updating";
}

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
  const commands = useTranslations("enums.KanbanCommand");
  const unmet = useUnmet();
  const router = useRouter();
  const hint = useId();
  const held = useHeldCommand();
  const [, startTransition] = useTransition();
  const [book] = useState(() => new AnsweredCards());
  const answered = useSyncExternalStore(book.subscribe, book.snapshot, book.snapshot);
  const [selected, setSelected] = useState<string>();
  const [dragged, setDragged] = useState<string>();
  const [writing, setWriting] = useState<string>();
  const [asking, setAsking] = useState<Asking>();
  const [notices, setNotices] = useState<Readonly<Record<string, Notice>>>({});
  // The sentence told, and how many were: the same sentence told again is a new node of the live
  // region, so that it is announced again.
  const [announced, setAnnounced] = useState({ text: "", count: 0 });
  // Whether the tasks are being read anew, since the answer of a gesture; whether that reading was
  // over without bringing the answers (`failed`).
  const [reading, reread] = useTransition();
  const wasReading = useRef(false);
  const failed = useSyncExternalStore(book.subscribe, book.lapsed, book.lapsed);
  const [focusing, setFocusing] = useState<{ readonly id: string; readonly form: boolean }>();
  const elements = useRef(new Map<string, HTMLElement>());
  const date = useRef<HTMLInputElement | null>(null);
  // The card chosen now, set at the very moment it is: an answer comes back after the user may
  // have chosen another card, and the focus must not be taken from that one.
  const chosen = useRef<string>(undefined);
  const shown = useMemo(() => replaced(columns, answered), [columns, answered]);
  // The one stop of Tab of the board: the card chosen, else the first card. The arrows go from card
  // to card (WF-IHM-0100).
  const tabStop = useMemo(() => {
    const all = COLUMNS.flatMap(([state]) => shown[state]);
    return all.find((card) => card.node_id === selected)?.node_id ?? all[0]?.node_id;
  }, [shown, selected]);

  // An answer the columns read since overtake is forgotten, so that a later reading at an older
  // version — a page read before the write was seen — cannot bring it back. Done once the reading
  // is committed, never while it renders.
  useLayoutEffect(() => {
    book.read(columns);
  }, [book, columns]);

  // A reading over that leaves an answer unreached has not brought the card its version: it is not
  // up to date, until it is read anew. Judged as the reading ends, once the layout effect above has
  // forgotten the answers the columns read overtake, never by the time the reading takes.
  useEffect(() => {
    if (reading) {
      wasReading.current = true;
      return;
    }
    if (wasReading.current) {
      wasReading.current = false;
      if (Object.keys(book.snapshot()).length > 0) {
        book.lapse();
      }
    }
  }, [book, reading]);

  // The focus follows the card moved, which another column mounts anew, or the field of the date.
  useEffect(() => {
    if (focusing === undefined) {
      return;
    }
    (focusing.form ? date.current : elements.current.get(focusing.id))?.focus();
  }, [focusing]);

  /** Read the tasks anew, the cards answered being marked until it is over. */
  const readAnew = () => {
    book.settle();
    reread(() => {
      router.refresh();
    });
  };

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
    book.settle();
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
        // A task the API refuses for its state, or for a version past, is no more what the card
        // shows: the tasks are read anew.
        if (outcome.kind === "conflict" || outcome.kind === "stale") {
          readAnew();
        }
        return;
      }
      const node = outcome.data.nodes.find((each) => each.node_id === card.node_id);
      const state = node?.task?.progress;
      if (node !== undefined && state !== undefined) {
        book.answer(cardOf(node, state));
        setAnnounced(({ count }) => ({
          text: t("moved", { label: card.label, column: titleOf(state) }),
          count: count + 1,
        }));
      } else {
        // The answer does not say where the task is: the card stays, and says so, rather than
        // announce a move nobody saw.
        say(card.node_id, { kind: "said", sentence: t("unplaced", { label: card.label }) });
      }
      // The tasks are read anew either way: the card answered lists no gesture until they are.
      readAnew();
    });
  };

  /** Ask a gesture of a card: its date first when it happens on one, else at once. */
  const gesture = (card: KanbanCard, asked: CardGesture) => {
    if (writing !== undefined) {
      return;
    }
    // The date asked on a card is not replaced by another card's: its entry would be lost unseen.
    // A card no more in the reading shows no entry: its request holds nothing back.
    if (asking !== undefined && asking.id !== card.node_id && cards.has(asking.id)) {
      say(card.node_id, { kind: "said", sentence: t("asking") });
      return;
    }
    if (DATED.has(asked.command)) {
      setAsking({ id: card.node_id, gesture: asked });
      setFocusing({ id: card.node_id, form: true });
      return;
    }
    write(card, asked, undefined);
  };

  /** Carry a card to a column — dropped on it, or by the keys: the gesture it lists, or why not. */
  const carry = (card: KanbanCard, state: TaskProgress) => {
    if (card.state === state || writing !== undefined) {
      return;
    }
    const leading = gestureToward(card, state);
    if (leading === undefined) {
      say(card.node_id, { kind: "said", sentence: t("noGesture", { column: titleOf(state) }) });
      return;
    }
    if (!leading.is_available) {
      say(card.node_id, {
        kind: "said",
        sentence: t("gestureUnavailable", {
          command: commands(leading.command),
          conditions: unmet(leading),
        }),
      });
      return;
    }
    say(card.node_id, undefined);
    gesture(card, leading);
  };

  const actions: CardActions = {
    remaining,
    hint,
    selected,
    tabStop,
    dragged,
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
    focusFrom: (id, key) => {
      const target = focusOf(shown, id, key);
      if (target === undefined) {
        return false;
      }
      elements.current.get(target)?.focus();
      return true;
    },
    carryFrom: (card, key) => {
      const state = carriedTo(shown, card.node_id, key);
      if (state === undefined) {
        return false;
      }
      carry(card, state);
      return true;
    },
    drag: setDragged,
    gesture,
    date: write,
    cancel: (id) => {
      setAsking(undefined);
      setFocusing({ id, form: false });
    },
    retry: (id) => {
      readAnew();
      // The button of the retry is gone once the card is marked again: the focus goes to the card.
      setFocusing({ id, form: false });
    },
    forget: (id) => {
      say(id, undefined);
      setFocusing({ id, form: false });
    },
  };

  const cards = new Map(
    COLUMNS.flatMap(([state]) => shown[state].map((card) => [card.node_id, card] as const)),
  );
  const moving = dragged === undefined ? undefined : cards.get(dragged);
  const drop = (event: DragEvent<HTMLElement>, state: TaskProgress) => {
    event.preventDefault();
    setDragged(undefined);
    if (moving !== undefined) {
      carry(moving, state);
    }
  };

  return (
    <div className="space-y-3">
      <p id={hint} className="text-xs text-muted-foreground">
        {t("keys")}
      </p>
      <p role="status" className="sr-only">
        {announced.count === 0 ? null : <span key={announced.count}>{announced.text}</span>}
      </p>
      <div className="grid gap-4 sm:grid-cols-3">
        {COLUMNS.map(([state, title]) => {
          const listed = shown[state];
          const reachable =
            moving !== undefined &&
            moving.state !== state &&
            gestureToward(moving, state)?.is_available === true;
          return (
            <section
              key={state}
              aria-label={t(title)}
              onDragOver={(event) => {
                if (moving !== undefined) {
                  event.preventDefault();
                  event.dataTransfer.dropEffect = "move";
                }
              }}
              onDrop={(event) => {
                drop(event, state);
              }}
              className={`space-y-2 rounded-md ${
                reachable ? "outline-2 outline-dashed outline-offset-4 outline-ring" : ""
              }`}
            >
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
                        reading: readingOf(answered[card.node_id], failed),
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
