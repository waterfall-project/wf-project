// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The gestures that add and remove tasks and lines in a grid of the structure (US-0460,
 * WF-PLA-0070, WF-PLA-0130, WF-DEV-0050, WF-RAE-0040): « Insert below » a task or a line, « Insert
 * a sub-task », « Insert a line », « Delete », from the menu of a cell — on its row — and from the
 * keys: Insert, Alt+Insert, Ctrl+Insert, Ctrl+Delete (`structure-rules.ts`); the bar of the grid,
 * kept to one line, offers only the first task of a grid with no row to act on. The same writes
 * from the planning, the estimate and the remaining to commit (`createNode`, `deleteNode`): which
 * grid offers them is the command of the structure it reads, never a phase the front deduces — the
 * screen hands the gestures what the structure lists available (`tasks`, `lines`).
 *
 * A node is created from a dialog that names it — the label of a task; the label, the category and
 * the quantity of a line, which the contract requires —, and the row it acts on; the task inserted
 * below the row at the place after it among its siblings, a sub-task or a line at the end of the
 * row. The deletion of a summary, which carries its subordinates away, is confirmed first; that of
 * a task without subordinates or of a line is not, and the focus goes back to the active cell once
 * the grid is read anew. The grid is read anew once a write is answered, a creation or a deletion
 * renumbering the rows and moving their levels — the server's reading prevails (decision of the
 * author of 2026-10-19, #1160); the version the structure moved on to is told to the grid, which a
 * paste carries.
 *
 * A refusal — a task completed, for one — is told above the grid as any outcome, in the alert,
 * naming the row it was asked from, and that row is marked and described by it; that of a task
 * created from the bar, with no row, names the task tried. What was done is said in a status of its
 * own (`useSaid`). A write under way holds the commands, inactive and saying so; an answer closes
 * only the dialog it was sent from (défaut n° 24), and belongs to the structure it was written in
 * (défaut n° 1).
 */
"use client";

import { CornerDownRight, ListPlus, Plus, Trash2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import {
  type MouseEvent,
  type ReactNode,
  useEffect,
  useId,
  useRef,
  useState,
  useTransition,
} from "react";

import { createNode, deleteNode } from "@/api/actions/nodes";
import type { Outcome } from "@/api/problem";
import { useHeldCommand } from "@/components/commands/held";
import { UNAVAILABLE } from "@/components/commands/offer";
import { OutcomeNotice, refusalDescription } from "@/components/commands/outcome-notice";
import { type Said, useSaid } from "@/components/notices/said";
import { Button } from "@/components/ui/button";
import { ContextMenuItem } from "@/components/ui/context-menu";
import { Dialog, DialogContent } from "@/components/ui/dialog";

import type { GridNode, NodesWritten } from "./nodes";
import { CreateForm, DeleteConfirmation } from "./structure-dialogs";
import {
  bodyOf,
  type Entered,
  GESTURE_KEYS,
  type Gesture,
  gestureOfKey,
  gesturesOn,
  labelOf,
  type StructureGestures,
} from "./structure-rules";
import type { RowCommands } from "./undo-commands";

/** The icon of each gesture. */
const ICONS: Readonly<Record<Gesture, ReactNode>> = {
  first: <Plus aria-hidden="true" />,
  below: <Plus aria-hidden="true" />,
  child: <CornerDownRight aria-hidden="true" />,
  line: <ListPlus aria-hidden="true" />,
  delete: <Trash2 aria-hidden="true" />,
};

/** The cell a tree grid keeps active, the one stop of its tabulation. */
const ACTIVE_CELL = '[role="treegrid"] [tabindex="0"]';

/** A gesture open in a dialog: which, on what row, what opened it, and the how-many-th opening. */
interface Opened<Row extends GridNode> {
  readonly gesture: Gesture;
  readonly row: Row | undefined;
  readonly trigger: HTMLElement | undefined;
  readonly opening: number;
}

/** What the last write answered, for the structure it was written in. */
interface Told<Row extends GridNode> {
  readonly structure: string;
  readonly refusal: Refusal<Row>;
}

/**
 * A write refused: the outcome, the row it was asked from — none for the first task of a grid with
 * no row —, and the node it was about, by its label.
 */
interface Refusal<Row extends GridNode> {
  readonly outcome: Outcome<unknown>;
  readonly row: Row | undefined;
  readonly subject: string;
}

/** Give the focus back to what opened a dialog, or to the active cell of the grid. */
function refocus(trigger: HTMLElement | undefined): void {
  const target = trigger?.isConnected === true ? trigger : document.querySelector(ACTIVE_CELL);
  if (target instanceof HTMLElement) {
    target.focus();
  }
}

/** Whether a key was pressed in a field being entered, whose keys are its own. */
function entering(target: EventTarget): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

/** The dialog a gesture opens: the confirmation of a deletion, or the form of a creation. */
function GestureDialog<Row extends GridNode>({
  opened,
  scope,
  title,
  under,
  writing,
  onCreate,
  onDelete,
  onClose,
}: {
  readonly opened: Opened<Row>;
  readonly scope: StructureGestures;
  readonly title: string;
  readonly under: string | undefined;
  readonly writing: boolean;
  readonly onCreate: (entered: Entered) => void;
  readonly onDelete: () => void;
  readonly onClose: () => void;
}) {
  const { gesture, row, trigger } = opened;
  return (
    <Dialog
      open
      onOpenChange={(next) => {
        if (!next) {
          onClose();
        }
      }}
    >
      <DialogContent
        aria-busy={writing}
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          refocus(trigger);
        }}
      >
        {gesture === "delete" ? (
          <DeleteConfirmation
            label={row === undefined ? "" : labelOf(row)}
            pending={writing}
            onConfirm={onDelete}
            onCancel={onClose}
          />
        ) : (
          <CreateForm
            created={gesture === "line" ? "line" : "task"}
            title={title}
            under={under}
            categories={scope.categories ?? []}
            pending={writing}
            onCreate={onCreate}
            onCancel={onClose}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

/**
 * What the gestures put around the grid: the refusal as any outcome says it, in an alert that names
 * the row it was asked from — or the task tried, for a first task —; what the last write did, said
 * in a status.
 */
function GestureNotice<Row extends GridNode>({
  told,
  said,
  id,
  onClear,
}: {
  readonly told: Told<Row> | undefined;
  readonly said: Said | undefined;
  readonly id: string;
  readonly onClear: () => void;
}) {
  const t = useTranslations("grid.structure");
  const refusal = told?.refusal;
  const lead = (): string | undefined => {
    if (refusal === undefined) {
      return undefined;
    }
    return refusal.row === undefined
      ? t("refusedCreating", { label: refusal.subject })
      : t("refusedAt", { number: refusal.row.row_number, label: labelOf(refusal.row) });
  };
  return (
    <>
      <OutcomeNotice
        id={id}
        outcome={refusal?.outcome}
        subject={refusal?.subject}
        lead={lead()}
        onClear={onClear}
        onDismissed={() => {
          refocus(undefined);
        }}
        dismissible
      />
      <p role="status" aria-live="polite" className="text-sm empty:sr-only">
        {said === undefined ? null : <span key={said.count}>{said.text}</span>}
      </p>
    </>
  );
}

/**
 * The gestures of structure a grid gives its rows, as the structure it reads lists its commands:
 * none for a grid that offers none. Pass `onWritten` to be told the version the structure moved on
 * to.
 */
export function useStructureGestures<Row extends GridNode>(
  scope: StructureGestures | undefined,
  onWritten?: (written: NodesWritten) => void,
): RowCommands<Row> | undefined {
  const t = useTranslations("grid.structure");
  const router = useRouter();
  const held = useHeldCommand();
  const [, refresh] = useTransition();
  const [said, say] = useSaid();
  const noticeId = useId();
  const [opened, setOpened] = useState<Opened<Row>>();
  const [writing, setWriting] = useState(false);
  const [told, setTold] = useState<Told<Row>>();
  const openings = useRef(0);
  // The cell that had the focus when a row was deleted with no dialog: once the grid is read anew
  // without it, the focus goes back to the active cell, not to the page.
  const lost = useRef<HTMLElement>(undefined);
  useEffect(() => {
    if (lost.current !== undefined && !lost.current.isConnected) {
      lost.current = undefined;
      refocus(undefined);
    }
  });
  if (scope === undefined) {
    return undefined;
  }
  const structure = scope.structure.structure_id;
  const shown = told?.structure === structure ? told : undefined;
  const names: Readonly<Record<Gesture, string>> = {
    first: t("insertFirst"),
    below: t("insertBelow"),
    child: t("insertChild"),
    line: t("insertLine"),
    delete: t("delete"),
  };

  /** Send a write, and take its answer: the grid read anew when done, the refusal told otherwise. */
  const send = (
    call: () => Promise<Outcome<NodesWritten>>,
    row: Row | undefined,
    node: { readonly label: string; readonly done: string },
    opening: number | undefined,
    cell?: HTMLElement,
  ) => {
    setWriting(true);
    void held(call()).then((outcome) => {
      setWriting(false);
      // A dialog is closed by the answer to what it sent, never by one it did not send.
      if (opening === undefined || opening === openings.current) {
        setOpened(undefined);
      }
      if (outcome.kind === "done") {
        onWritten?.(outcome.data);
        setTold(undefined);
        say(node.done, { object: node.label });
        lost.current = cell;
        refresh(() => {
          router.refresh();
        });
      } else {
        setTold({ structure, refusal: { outcome, row, subject: node.label } });
      }
    });
  };
  const remove = (row: Row, opening: number | undefined, cell?: HTMLElement) => {
    const label = labelOf(row);
    send(
      () => deleteNode(scope.structure, row.node_id),
      row,
      { label, done: t("deleted", { label }) },
      opening,
      cell,
    );
  };
  const open = (gesture: Gesture, row: Row | undefined, trigger: HTMLElement | undefined) => {
    if (writing) {
      return;
    }
    if (gesture === "delete" && row !== undefined && row.task?.is_summary !== true) {
      remove(row, undefined, trigger);
      return;
    }
    openings.current += 1;
    setOpened({ gesture, row, trigger, opening: openings.current });
  };
  const close = () => {
    if (!writing) {
      setOpened(undefined);
    }
  };
  const create = (current: Opened<Row>, entered: Entered) => {
    send(
      () => createNode(scope.structure, bodyOf(current.gesture, current.row, entered)),
      current.row,
      { label: entered.label, done: t("created", { label: entered.label }) },
      current.opening,
    );
  };
  // A deletion needs a confirmation of its own only for a summary, which carries others away.
  const confirms = (gesture: Gesture, row: Row | undefined) =>
    gesture !== "delete" || row?.task?.is_summary === true;
  return {
    // The bar offers the first task of a grid with no row to act on — empty, or on its header —;
    // the others are offered by the menu of a cell and by the keys, which keep the bar to one line.
    bar: (row) =>
      row !== undefined || !gesturesOn(undefined, scope).includes("first") ? null : (
        <Button
          type="button"
          variant="outline"
          size="icon"
          aria-label={names.first}
          title={names.first}
          aria-disabled={writing ? true : undefined}
          aria-busy={writing}
          aria-keyshortcuts={GESTURE_KEYS.first}
          className={`size-7 shrink-0 ${UNAVAILABLE}`}
          onClick={(event: MouseEvent<HTMLElement>) => {
            open("first", undefined, event.currentTarget);
          }}
        >
          {ICONS.first}
        </Button>
      ),
    menu: (row, { cell, took }) =>
      gesturesOn(row, scope).map((gesture) => (
        <ContextMenuItem
          key={gesture}
          aria-disabled={writing ? true : undefined}
          aria-keyshortcuts={GESTURE_KEYS[gesture]}
          className={UNAVAILABLE}
          onSelect={(event) => {
            // Pressed while a write is under way, it does nothing, and the menu stays open.
            if (writing) {
              event.preventDefault();
              return;
            }
            // A dialog takes the focus; a deletion with nothing to confirm leaves it to the cell.
            if (confirms(gesture, row)) {
              took();
            }
            open(gesture, row, cell);
          }}
        >
          {ICONS[gesture]}
          {names[gesture]}
        </ContextMenuItem>
      )),
    keys: (row, event) => {
      const gesture = gestureOfKey(row, event);
      if (
        gesture === undefined ||
        opened !== undefined ||
        entering(event.target) ||
        !gesturesOn(row, scope).includes(gesture)
      ) {
        return false;
      }
      open(gesture, row, event.target instanceof HTMLElement ? event.target : undefined);
      return true;
    },
    around: (
      <>
        <GestureNotice
          told={shown}
          said={said}
          id={noticeId}
          onClear={() => {
            setTold(undefined);
          }}
        />
        {opened === undefined ? null : (
          <GestureDialog
            opened={opened}
            scope={scope}
            title={names[opened.gesture]}
            under={
              opened.row === undefined || opened.gesture === "delete"
                ? undefined
                : t("onRow", { number: opened.row.row_number, label: labelOf(opened.row) })
            }
            writing={writing}
            onCreate={(entered) => {
              create(opened, entered);
            }}
            onDelete={() => {
              if (opened.row !== undefined) {
                remove(opened.row, opened.opening, opened.trigger);
              }
            }}
            onClose={close}
          />
        )}
      </>
    ),
    refused:
      shown?.refusal.row === undefined
        ? undefined
        : {
            row: shown.refusal.row,
            described: refusalDescription(shown.refusal.outcome, noticeId),
          },
  };
}
