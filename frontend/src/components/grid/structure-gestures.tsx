// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The gestures that add, move and remove tasks and lines in a grid of the structure (US-0460,
 * WF-PLA-0070, WF-PLA-0080, WF-PLA-0130, WF-DEV-0050, WF-RAE-0040): « Insert below » a task or a
 * line, « Insert a sub-task », « Insert a line », « Indent », « Outdent », « Move up », « Move
 * down », « Delete », from the menu of a cell — on its row, or on the selection it stands in — and
 * from the keys: Insert, Alt+Insert, Ctrl+Insert, Alt+Shift and the arrows, Ctrl+Delete
 * (`structure-rules.ts`), and by the rows the handles of the grid drag (`RowDrag`); the bar of the
 * grid, kept to one line, offers only the first task of a grid with no row to act on. The same
 * writes from the planning, the estimate and the remaining to commit (`createNode`, `deleteNode`):
 * which grid offers them is the command of the structure it reads, never a phase the front deduces
 * — the screen hands the gestures what the structure lists available (`tasks`, `lines`).
 *
 * An indentation moves the tasks under the one that precedes the first, in the last place, an
 * outdentation after their parent, under the parent of that one, as MS Project does; up and down
 * move them by a rank among their siblings; rows dropped go before, after or under the row they are
 * dropped on (`moveNodes`): a task takes its subordinates with it, and no dialog asks anything. The
 * grid is read anew, the ancestors recalculated and the tasks redated taking the place of the rows
 * read; a refusal — a link a summary would hold to its subordinate, a loop, a node that is no
 * sibling — is told at the row, and the last, which comes from a reading gone stale, reads the grid
 * anew, the focus kept in the grid. A move, or a drop, is offered only where the rows shown hold
 * the neighbour it rests on (`structure-rules.ts`).
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
 * own (`useSaid`). A write under way, and the reading anew that follows it, hold the commands,
 * inactive and saying so, and accept no drop: the next move starts from the neighbours that reading
 * shows, never from those before it with a version already moved on. An answer closes only the
 * dialog it was sent from (défaut n° 24), and belongs to the structure it was written in (défaut
 * n° 1). The row a move was asked from — the first of the rows dropped — is told the grid
 * (`moved`), whose active cell follows it through the reading; the grid says it is busy as long as
 * the gestures wait (`busy`).
 */
"use client";

import {
  ArrowDown,
  ArrowUp,
  CornerDownRight,
  ListIndentDecrease,
  ListIndentIncrease,
  ListPlus,
  Plus,
  Trash2,
} from "lucide-react";
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

import { createNode, deleteNode, moveNodes } from "@/api/actions/nodes";
import { createTimeline } from "@/api/actions/projects";
import type { Outcome } from "@/api/problem";
import { useHeldCommand } from "@/components/commands/held";
import { UNAVAILABLE } from "@/components/commands/offer";
import { OutcomeNotice, refusalDescription } from "@/components/commands/outcome-notice";
import { type Said, useSaid } from "@/components/notices/said";
import { Button } from "@/components/ui/button";
import { ContextMenuItem } from "@/components/ui/context-menu";
import { Dialog, DialogContent } from "@/components/ui/dialog";

import type { GridNode, NodesWritten } from "./nodes";
import { byField } from "./planning-attachment";
import type { RowChange, RowChoices, RowsApplied } from "./row-choices";
import { ChoiceMenuItems, targetsOf, TimelineForm, writeChange } from "./choice-menu";
import type { DropPlace } from "./row-selection";
import { CreateForm, DeleteConfirmation } from "./structure-dialogs";
import {
  bodyOf,
  dropOf,
  type Entered,
  GESTURE_KEYS,
  type Gesture,
  gestureOfKey,
  gesturesOn,
  labelOf,
  moveOf,
  type Moving,
  moves,
  type StructureGestures,
  topsOf,
} from "./structure-rules";
import type { RowCommands } from "./undo-commands";

/** The icon of each gesture. */
const ICONS: Readonly<Record<Gesture, ReactNode>> = {
  first: <Plus aria-hidden="true" />,
  below: <Plus aria-hidden="true" />,
  child: <CornerDownRight aria-hidden="true" />,
  line: <ListPlus aria-hidden="true" />,
  indent: <ListIndentIncrease aria-hidden="true" />,
  outdent: <ListIndentDecrease aria-hidden="true" />,
  up: <ArrowUp aria-hidden="true" />,
  down: <ArrowDown aria-hidden="true" />,
  delete: <Trash2 aria-hidden="true" />,
};

/** What a move says it did, by the gesture that asked it — or rows dropped. */
const DONE = { indent: "indented", outdent: "outdented", up: "up", down: "down" } as const;
type Done = (typeof DONE)[Moving] | "dropped";

/** The cell a tree grid keeps active, the one stop of its tabulation. */
const ACTIVE_CELL = '[role="treegrid"] [tabindex="0"]';

/** A gesture open in a dialog: which, on what row, what opened it, and the how-many-th opening. */
interface Opened<Row extends GridNode> {
  readonly gesture: Gesture;
  readonly row: Row | undefined;
  readonly trigger: HTMLElement | undefined;
  readonly opening: number;
}

/** The timeline being named, and the rows it is inscribed to once it exists. */
interface Naming<Row extends GridNode> {
  readonly rows: readonly Row[];
  readonly applied: (written: RowsApplied<Row>) => void;
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
 * none for a grid that offers none. `onWritten` is told what each write answered, whose version the
 * grid keeps (`useStructureVersion`) and brings back in `scope.version`, which the next move carries.
 * `choices` gives the menu of the cells the submenus of the timelines of a task and of the sub-project
 * of a line (US-0480): the same writes, the same reading anew, the same refusals told at the row.
 */
export function useStructureGestures<Row extends GridNode>(
  scope: StructureGestures | undefined,
  onWritten: (written: NodesWritten) => void,
  choices?: RowChoices<Row>,
): RowCommands<Row> | undefined {
  const t = useTranslations("grid.structure");
  const router = useRouter();
  const held = useHeldCommand();
  const [reading, refresh] = useTransition();
  const [said, say] = useSaid();
  const noticeId = useId();
  const [opened, setOpened] = useState<Opened<Row>>();
  const [writing, setWriting] = useState(false);
  const [told, setTold] = useState<Told<Row>>();
  const [moved, setMoved] = useState<{ readonly row: Row; readonly count: number }>();
  const [naming, setNaming] = useState<Naming<Row>>();
  const openings = useRef(0);
  // The cell that had the focus when a row was deleted with no dialog: once the grid is read anew
  // without it, the focus goes back to the active cell, not to the page. It is forgotten as soon as
  // that reading is over, whether the cell was removed or not, and the focus is only given back
  // when it is on the page, never taken from a field the user went to.
  const lost = useRef<HTMLElement>(undefined);
  useEffect(() => {
    const cell = lost.current;
    if (cell === undefined) {
      return;
    }
    if (!cell.isConnected) {
      lost.current = undefined;
      if (document.activeElement === null || document.activeElement === document.body) {
        refocus(undefined);
      }
    } else if (!reading) {
      // The reading that follows a write shows as pending from the first render after it: a render
      // that finds it not pending is one the transition was not seen in, and the cell is
      // forgotten, not kept for a removal that has nothing to do with the write.
      lost.current = undefined;
    }
  });
  if (scope === undefined) {
    return undefined;
  }
  const structure = scope.structure.structure_id;
  // A gesture waits for the write and for the reading anew that follows it.
  const busy = writing || reading;
  const shown = told?.structure === structure ? told : undefined;
  const names: Readonly<Record<Gesture, string>> = {
    first: t("insertFirst"),
    below: t("insertBelow"),
    child: t("insertChild"),
    line: t("insertLine"),
    indent: t("indent"),
    outdent: t("outdent"),
    up: t("up"),
    down: t("down"),
    delete: t("delete"),
  };
  /** Send a write, and take its answer: the grid read anew when done, the refusal told otherwise. */
  const send = (
    call: () => Promise<Outcome<NodesWritten>>,
    row: () => Row | undefined,
    node: {
      readonly label: string;
      readonly done: string;
      readonly moves?: Row;
      /** The answers were told to `onWritten` one by one, as they came. */
      readonly reported?: true;
    },
    opening: number | undefined,
    cell?: HTMLElement,
  ) => {
    setWriting(true);
    // A refusal by field is told by the reason of its field — a node to follow that is no sibling —,
    // the envelope saying only that the entry is invalid.
    void held(call().then(byField)).then((outcome) => {
      setWriting(false);
      // A dialog is closed by the answer to what it sent, never by one it did not send.
      if (opening === undefined || opening === openings.current) {
        setOpened(undefined);
        setNaming(undefined);
      }
      if (outcome.kind === "done") {
        if (node.reported !== true) {
          onWritten(outcome.data);
        }
        setTold(undefined);
        say(node.done, { object: node.label });
        const { moves: bore } = node;
        if (bore !== undefined) {
          setMoved((before) => ({ row: bore, count: (before?.count ?? 0) + 1 }));
        }
        lost.current = cell;
        refresh(() => {
          router.refresh();
        });
      } else {
        setTold({ structure, refusal: { outcome, row: row(), subject: node.label } });
        // A node to follow that is no sibling comes from a reading gone stale: read it anew, the
        // focus given back to the grid should the reading remove the cell that had it.
        if (outcome.kind !== "unreachable" && outcome.problem.code === "NODE_NOT_SIBLING") {
          lost.current = cell;
          refresh(() => {
            router.refresh();
          });
        }
      }
    });
  };
  const remove = (row: Row, opening: number | undefined, cell?: HTMLElement) => {
    const label = labelOf(row);
    send(
      () => deleteNode(scope.structure, row.node_id, row.lock_version),
      () => row,
      { label, done: t("deleted", { label }) },
      opening,
      cell,
    );
  };
  /**
   * Move the rows acted on — the selection, or the row alone —, the subordinates they bear with
   * them, and read the grid anew: told by the first of the nodes that bear them, and how many others.
   */
  const move = (
    body: ReturnType<typeof moveOf>,
    from: Row | undefined,
    acted: readonly Row[],
    done: Done,
    cell: HTMLElement | undefined,
  ) => {
    const tops = topsOf(acted, scope.rows);
    const [first] = tops;
    if (body === undefined || first === undefined) {
      return;
    }
    const label = labelOf(first);
    send(
      () => moveNodes(scope.structure, body),
      () => first,
      { label, done: t(`moved.${done}`, { label, others: tops.length - 1 }), moves: from ?? first },
      undefined,
      cell,
    );
  };
  const open = (
    gesture: Gesture,
    row: Row | undefined,
    acted: readonly Row[],
    trigger: HTMLElement | undefined,
  ) => {
    if (busy) {
      return;
    }
    if (moves(gesture)) {
      move(moveOf(gesture, acted, scope), row, acted, DONE[gesture], trigger);
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
      () => current.row,
      { label: entered.label, done: t("created", { label: entered.label }) },
      current.opening,
    );
  };
  /**
   * Write a change of the submenus on the rows it applies to, one write per row with its version,
   * each answer taking the place of the row read, and the grid read anew: told by the first of the
   * rows, and how many others. A refusal is told for the row it was made at; the rows before it stay
   * written. With `timeline`, the timeline is created first, named, and the rows are inscribed to it.
   */
  const choose = (
    change: RowChange,
    acted: readonly Row[],
    applied: (written: RowsApplied<Row>) => void,
    timeline?: { readonly label: string; readonly opening: number },
  ) => {
    const [first, ...others] = choices === undefined ? [] : targetsOf(change, acted, choices);
    if (choices === undefined || first === undefined || busy) {
      return;
    }
    let refused: Row = first;
    const label = labelOf(first);
    const wrote = (written: NodesWritten) => {
      onWritten(written);
      applied(choices.written(written));
    };
    const call = async (): Promise<Outcome<NodesWritten>> => {
      let made = change;
      if (timeline !== undefined) {
        const created = await createTimeline(choices.tracking?.project ?? "", timeline.label);
        if (created.kind !== "done") {
          return created;
        }
        made = { kind: "timeline", id: created.data.timeline_id, on: true };
      }
      const { outcome, at } = await writeChange(
        scope.structure,
        choices,
        made,
        [first, ...others],
        wrote,
      );
      refused = at ?? first;
      return outcome;
    };
    send(
      call,
      () => refused,
      {
        label,
        done: t(change.kind === "subproject" ? "subprojectSet" : "tracked", {
          label,
          others: others.length,
        }),
        reported: true,
      },
      timeline?.opening,
    );
  };
  // A dialog asks only a creation and the deletion of a summary, which carries others away: a leaf
  // is deleted at once, and a move asks nothing.
  const confirms = (gesture: Gesture, row: Row | undefined) =>
    gesture === "delete" ? row?.task?.is_summary === true : !moves(gesture);
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
          aria-disabled={busy ? true : undefined}
          aria-busy={busy}
          aria-keyshortcuts={GESTURE_KEYS.first}
          className={`size-7 shrink-0 ${UNAVAILABLE}`}
          onClick={(event: MouseEvent<HTMLElement>) => {
            open("first", undefined, [], event.currentTarget);
          }}
        >
          {ICONS.first}
        </Button>
      ),
    menu: (row, { cell, took, rows, applied }) => {
      const gestures = gesturesOn(row, scope, rows);
      return (
        <>
          {gestures.map((gesture) => (
            <ContextMenuItem
              key={gesture}
              aria-disabled={busy ? true : undefined}
              aria-keyshortcuts={GESTURE_KEYS[gesture]}
              className={UNAVAILABLE}
              onSelect={(event) => {
                // Pressed while a write or its reading is under way, it does nothing, and the menu
                // stays open.
                if (busy) {
                  event.preventDefault();
                  return;
                }
                // A dialog takes the focus; a deletion with nothing to confirm leaves it to the cell.
                if (confirms(gesture, row)) {
                  took();
                }
                open(gesture, row, rows, cell);
              }}
            >
              {ICONS[gesture]}
              {names[gesture]}
            </ContextMenuItem>
          ))}
          {row === undefined || choices === undefined ? null : (
            <ChoiceMenuItems
              choices={choices}
              row={row}
              busy={busy}
              separated={gestures.length > 0}
              change={(change) => {
                choose(change, rows, applied);
              }}
              create={() => {
                took();
                openings.current += 1;
                setNaming({ rows, applied, trigger: cell, opening: openings.current });
              }}
            />
          )}
        </>
      );
    },
    keys: (row, event, rows) => {
      const gesture = gestureOfKey(row, event);
      if (gesture === undefined || opened !== undefined || entering(event.target)) {
        return false;
      }
      // A move not offered on a row — the first of its siblings asked up — is taken, and does
      // nothing: Alt, Shift and an arrow would otherwise move the active cell as the arrow alone does.
      if (!gesturesOn(row, scope, rows).includes(gesture)) {
        return row !== undefined && moves(gesture);
      }
      open(gesture, row, rows, event.target instanceof HTMLElement ? event.target : undefined);
      return true;
    },
    // The grid drops nothing while the gestures wait (`busy`). The cell that has the focus — the
    // handle the drag started from — is given back its focus, should the reading anew no longer
    // show the rows dropped, under a summary folded for one.
    drag: {
      accepts: (rows, target, place: DropPlace) => dropOf(rows, target, place, scope) !== undefined,
      drop: (rows, target, place) => {
        const cell = document.activeElement?.closest("td[data-row]");
        move(
          dropOf(rows, target, place, scope),
          undefined,
          rows,
          "dropped",
          cell instanceof HTMLElement ? cell : undefined,
        );
      },
    },
    moved: moved === undefined ? undefined : { ...moved, settled: !reading },
    busy,
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
        {naming === undefined ? null : (
          <Dialog
            key={naming.opening}
            open
            onOpenChange={(next) => {
              if (!next && !writing) {
                setNaming(undefined);
              }
            }}
          >
            <DialogContent
              aria-busy={writing}
              onCloseAutoFocus={(event) => {
                event.preventDefault();
                refocus(naming.trigger);
              }}
            >
              <TimelineForm
                pending={writing}
                onCreate={(label) => {
                  choose({ kind: "timeline", id: "", on: true }, naming.rows, naming.applied, {
                    label,
                    opening: naming.opening,
                  });
                }}
                onCancel={() => {
                  setNaming(undefined);
                }}
              />
            </DialogContent>
          </Dialog>
        )}
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
