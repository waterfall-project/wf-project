// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The selection of rows of a dense grid, and the dragging of what is selected (US-0460,
 * WF-IHM-0040, WF-IHM-0100): rows contiguous among those the grid shows, from an anchor to an end,
 * found by their identity, so that a reading anew that moves them keeps them selected. The cell of
 * the row number is the handle of its row: a click selects the row alone, Shift and a click extend
 * the selection from the anchor to it; from the keyboard, on the column of the handles, Space
 * selects the row of the active cell, Shift and the up or down arrow extend the selection as the
 * active cell moves, and Escape lifts it. Each row tells whether it is selected (`aria-selected`),
 * the grid that it takes several (`aria-multiselectable`), and a status how many are. The commands
 * of the screen act on the selection the row they start from stands in (Alt+Shift and an arrow, for
 * the structure).
 *
 * The handle drags the selection — or its own row alone, when it is not selected — beside another
 * row: before it or after it, at its level, by the upper or the lower quarter of the row, or under
 * it, by its middle; between two rows is before the lower one. The indicator of the drop is a line
 * between the rows, or the row shaded, and only where the screen accepts the place (`RowDrag`): the
 * screen says where rows go, and moves them — never while it says it is busy (`RowCommands.busy`,
 * which `drag` demands), the grid then dropping nothing. A drop is taken only of what the handles
 * drag, by its type (`DRAGGED_ROWS`).
 *
 * A grid whose screen drags nothing (`RowCommands.drag`) selects nothing, and shows no handle. The
 * active cell, in a row selected, follows its row through a reading anew that moves it, so that the
 * next move starts from the same rows; so does it the row a command moved (`RowCommands.moved`),
 * selected or not, once the reading that command asked comes, the focus given back to it unless it
 * went out of the grid — but only for a user who stayed where its answer left them: one gone on
 * with the arrows, or into a field, is left there. A focus on the body of the page counts as
 * nowhere, not as gone: a click out of the grid, on what takes no focus, leaves the move followed.
 * A reading anew that no longer shows an end of the selection — a filter, the folding of a row
 * that bears it — lifts it, rather than leave it to come back of itself; folding rows under the
 * selection, its ends shown, keeps it. The rows counted are those shown: the subordinates folded
 * under a summary selected go with it uncounted.
 */
"use client";

import { Check, GripVertical } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  type DragEvent,
  type KeyboardEvent,
  type MouseEvent,
  type RefObject,
  useLayoutEffect,
  useRef,
  useState,
} from "react";

import { TableCell } from "@/components/ui/table";
import { cn } from "@/components/ui/utils";

import { cellAttributes, type CellState, cellKeys } from "./cell-attributes";
import { ROW_NUMBER_KEY } from "./columns";
import { type CellPosition, type Cursor, HEADER_ROW, positionOf } from "./grid-keyboard";
import type { RowDragging, RowMoved } from "./undo-commands";

/**
 * The type of what the handles drag, the identities of its rows: of its own, so that a drop from
 * elsewhere — a text, a file — moves nothing.
 */
const DRAGGED_ROWS = "application/x-waterfall-rows";

/** Where rows dropped go, beside a row: before it or after it at its level, or under it, last. */
export type DropPlace = "before" | "after" | "into";

/** What a screen does of rows dragged: whether they may go beside a row, and their move there. */
export interface RowDrag<Row> {
  readonly accepts: (rows: readonly Row[], target: Row, place: DropPlace) => boolean;
  readonly drop: (rows: readonly Row[], target: Row, place: DropPlace) => void;
}

/** The selection, by the identity of its rows: the one it started from, and the one it ends on. */
interface Range {
  readonly anchor: string;
  readonly end: string;
}

/** Where rows dragged would go: beside the row at an index. */
interface Drop {
  readonly index: number;
  readonly place: DropPlace;
}

/** The first and the last index of a selection among rows, if both of its ends are among them. */
function boundsOf(
  range: Range | undefined,
  keys: (index: number) => string | undefined,
  count: number,
): readonly [number, number] | undefined {
  if (range === undefined) {
    return undefined;
  }
  let anchor = -1;
  let end = -1;
  for (let index = 0; index < count && (anchor < 0 || end < 0); index += 1) {
    const key = keys(index);
    anchor = key === range.anchor ? index : anchor;
    end = key === range.end ? index : end;
  }
  return anchor < 0 || end < 0 ? undefined : [Math.min(anchor, end), Math.max(anchor, end)];
}

/** The index of the row a handle stands in, if an event happened in a handle. */
function handleOf(target: EventTarget): number | undefined {
  const cell = target instanceof Element ? target.closest("td[data-column]") : null;
  const at = positionOf(cell);
  return at?.column === ROW_NUMBER_KEY ? at.row : undefined;
}

/** What a key asks of the selection, on a handle: Space, Shift and Space, Escape, Shift and an arrow. */
function selectionKey(
  event: KeyboardEvent<HTMLElement>,
): "select" | "extend" | "lift" | "up" | "down" | undefined {
  if (event.altKey || event.ctrlKey || event.metaKey) {
    return undefined;
  }
  const keys: Readonly<Partial<Record<string, "select" | "lift" | "up" | "down">>> = {
    " ": "select",
    Escape: "lift",
    ArrowUp: "up",
    ArrowDown: "down",
  };
  const key = keys[event.key];
  if (key === "select") {
    return event.shiftKey ? "extend" : key;
  }
  return key === "lift" || event.shiftKey ? key : undefined;
}

/** Where, beside the row of a cell, a pointer at a height drops: by the quarters of the row. */
function dropBeside(cell: Element, y: number, index: number, count: number): Drop {
  const box = cell.getBoundingClientRect();
  const offset = y - box.top;
  if (offset < box.height / 4) {
    return { index, place: "before" };
  }
  if (offset <= (box.height * 3) / 4) {
    return { index, place: "into" };
  }
  return index + 1 < count ? { index: index + 1, place: "before" } : { index, place: "after" };
}

/**
 * What the screen does of rows dropped, where it says it is not busy: none before the reading anew
 * of a move, which would go from the neighbours before it.
 */
function droppingOf<Row>(commands: RowDragging<Row> | undefined): RowDrag<Row> | undefined {
  return commands?.drag === undefined || commands.busy ? undefined : commands.drag;
}

/** The commands of a screen the selection reads: the drag, whether busy, the row last moved. */
type SelectionCommands<Row> = RowDragging<Row> & { readonly moved?: RowMoved<Row> | undefined };

/** What the grid of rows `Row` selects, and drags. */
export interface RowSelectionOptions<Row> {
  /** The rows the grid shows, in their order. */
  readonly rows: readonly Row[];
  readonly keyOf: (row: Row) => string;
  /**
   * The commands of the screen: what it does of rows dragged — none, and the grid selects nothing
   * —, whether it is busy, and the row its last command moved.
   */
  readonly commands: SelectionCommands<Row> | undefined;
  readonly cursor: Cursor;
  /** Focus a cell, brought into view once it is rendered. */
  readonly focusAt: (at: CellPosition) => void;
  /** The element of the grid, which the focus is given back within. */
  readonly scroller: RefObject<HTMLElement | null>;
}

/** Rows read anew, the rows they replace, and the identity of a row. */
interface Reread<Row> {
  readonly seen: readonly Row[];
  readonly rows: readonly Row[];
  readonly keyOf: (row: Row) => string;
}

/**
 * The row the active cell goes to in rows read anew: that of the row a command moved, wherever the
 * rows show it; or, from a row selected, that row where it went. None, and the active cell stays.
 */
function followedRow<Row>(
  { seen, rows, keyOf }: Reread<Row>,
  range: Range | undefined,
  active: number,
  moved: Row | undefined,
): { readonly row: number; readonly moved: boolean } | undefined {
  const indexOf = (row: Row) => {
    const key = keyOf(row);
    return rows.findIndex((each) => keyOf(each) === key);
  };
  if (moved !== undefined) {
    const now = indexOf(moved);
    return now < 0 ? undefined : { row: now, moved: true };
  }
  const was = seen[active];
  const before = boundsOf(
    range,
    (index) => {
      const row = seen[index];
      return row === undefined ? undefined : keyOf(row);
    },
    seen.length,
  );
  if (was === undefined || before === undefined || active < before[0] || active > before[1]) {
    return undefined;
  }
  const now = indexOf(was);
  return now < 0 || now === active ? undefined : { row: now, moved: false };
}

/** The row a command moved, and the active cell its answer found. */
interface Following<Row> {
  readonly row: Row;
  readonly at: CellPosition;
  /** Follow it no more, through the readings anew to come of the same move. */
  readonly drop: () => void;
}

/**
 * The move a command told that the active cell follows: from its answer until the reading anew it
 * asked is over — the reading that brings the rows moved included —, never after; with the active
 * cell its answer found.
 */
function useFollowing<Row>(
  moved: RowMoved<Row> | undefined,
  active: CellPosition,
): Following<Row> | undefined {
  const [followed, setFollowed] = useState(0);
  const [answered, setAnswered] = useState<{ readonly count: number; readonly at: CellPosition }>();
  if (moved === undefined || moved.count === followed) {
    return undefined;
  }
  let at = answered?.count === moved.count ? answered.at : undefined;
  if (at === undefined) {
    at = active;
    setAnswered({ count: moved.count, at });
  }
  if (moved.settled) {
    setFollowed(moved.count);
  }
  return {
    row: moved.row,
    at,
    drop: () => {
      setFollowed(moved.count);
    },
  };
}

/**
 * Whether the user stayed where a move left them since its answer: the active cell is the one the
 * answer found, and the focus is on it, or nowhere — not gone to another cell, nor into a field.
 * Nowhere is no element, or the body of the page, where a click on what takes no focus leaves it.
 * It reads the focus of the document during the render that takes the reading anew: the focus is
 * no state of React, and that render is the one moment the reading is compared with the answer.
 */
function stayed(
  at: CellPosition,
  active: CellPosition,
  scroller: RefObject<HTMLElement | null>,
): boolean {
  if (active.row !== at.row || active.column !== at.column) {
    return false;
  }
  const { activeElement } = document;
  if (activeElement === null || activeElement === document.body) {
    return true;
  }
  const focused = positionOf(activeElement);
  return (
    scroller.current?.contains(activeElement) === true &&
    focused?.row === at.row &&
    focused.column === at.column
  );
}

/**
 * The row moved that a reading anew takes the active cell to: followed only by a user who stayed
 * where the move left them; one gone on with the arrows, or into a field, keeps where they went, and
 * the move is followed no more.
 */
function movedFollowed<Row>(
  following: Following<Row> | undefined,
  active: CellPosition,
  scroller: RefObject<HTMLElement | null>,
): Row | undefined {
  if (following === undefined) {
    return undefined;
  }
  if (!stayed(following.at, active, scroller)) {
    following.drop();
    return undefined;
  }
  return following.row;
}

/**
 * Give the focus to the cell a moved row took, once it is rendered — unless it went out of the grid
 * meanwhile, to a field the user went to.
 */
function useTakenFocus(
  focusAt: (at: CellPosition) => void,
  scroller: RefObject<HTMLElement | null>,
): (at: CellPosition) => void {
  const [taken, setTaken] = useState<{ readonly at: CellPosition; readonly count: number }>();
  const focused = useRef(0);
  useLayoutEffect(() => {
    if (taken === undefined || taken.count === focused.current) {
      return;
    }
    focused.current = taken.count;
    const { activeElement } = document;
    if (
      activeElement === null ||
      activeElement === document.body ||
      scroller.current?.contains(activeElement) === true
    ) {
      focusAt(taken.at);
    }
  });
  return (at) => {
    setTaken((before) => ({ at, count: (before?.count ?? 0) + 1 }));
  };
}

/** Select rows of a grid, and drag them. */
export function useRowSelection<Row>({
  rows,
  keyOf,
  commands,
  cursor,
  focusAt,
  scroller,
}: RowSelectionOptions<Row>) {
  const dropping = droppingOf(commands);
  const [range, setRange] = useState<Range>();
  const [drop, setDrop] = useState<Drop>();
  // The rows dragged, by their identity, while a drag is under way.
  const dragged = useRef<readonly string[]>(undefined);
  const keyAt = (index: number) => {
    const row = rows[index];
    return row === undefined ? undefined : keyOf(row);
  };
  const offered = commands?.drag !== undefined;
  const bounds = offered ? boundsOf(range, keyAt, rows.length) : undefined;
  const following = useFollowing(commands?.moved, cursor.active);
  const take = useTakenFocus(focusAt, scroller);
  // The rows the active cell was among: a reading anew that moves the row a command moved, or the
  // row of the active cell, selected, takes the active cell with it.
  const [seen, setSeen] = useState(rows);
  if (seen !== rows) {
    setSeen(rows);
    if (range !== undefined && boundsOf(range, keyAt, rows.length) === undefined) {
      setRange(undefined);
    }
    const next = followedRow(
      { seen, rows, keyOf },
      range,
      cursor.active.row,
      movedFollowed(following, cursor.active, scroller),
    );
    if (next !== undefined) {
      const at = { row: next.row, column: cursor.active.column };
      cursor.set(at);
      if (next.moved) {
        take(at);
      }
    }
  }
  const isSelected = (index: number) =>
    bounds !== undefined && index >= bounds[0] && index <= bounds[1];
  /** The rows acted on from a row: the selection it stands in, or the row alone. */
  const acted = (index: number): readonly Row[] => {
    if (bounds !== undefined && isSelected(index)) {
      return rows.slice(bounds[0], bounds[1] + 1);
    }
    const row = rows[index];
    return row === undefined ? [] : [row];
  };
  /** Select the row at an index alone, or extend the selection to it. */
  const select = (index: number, extend: boolean) => {
    const key = keyAt(index);
    if (key === undefined) {
      return;
    }
    setRange((before) =>
      extend && before !== undefined && bounds !== undefined
        ? { anchor: before.anchor, end: key }
        : { anchor: key, end: key },
    );
  };
  const clear = () => {
    dragged.current = undefined;
    setDrop(undefined);
  };
  /** Extend the selection from the row at an index to the next one up or down, if there is one. */
  const extend = (from: number, step: number) => {
    const anchor = isSelected(from) ? range?.anchor : keyAt(from);
    const end = keyAt(from + step);
    if (anchor !== undefined && end !== undefined) {
      setRange({ anchor, end });
    }
  };
  /**
   * The keys of the selection, on the column of the handles: whether the grid takes the key —
   * Shift and an arrow extend the selection and leave the grid to move the active cell, but past
   * the first row, to the header.
   */
  const onKeyDown = (event: KeyboardEvent<HTMLElement>): boolean => {
    const at = positionOf(event.target);
    const key = offered && at?.column === ROW_NUMBER_KEY ? selectionKey(event) : undefined;
    if (at === undefined || key === undefined || at.row === HEADER_ROW) {
      return false;
    }
    if (key === "select" || key === "extend") {
      select(at.row, key === "extend");
      return true;
    }
    if (key === "lift") {
      setRange(undefined);
      return range !== undefined;
    }
    extend(at.row, key === "up" ? -1 : 1);
    return key === "up" && at.row === 0;
  };
  /** The rows the drag under way carries, in the order of the grid. */
  const carried = (): readonly Row[] =>
    rows.filter((row) => dragged.current?.includes(keyOf(row)) === true);
  /** Where a pointer over the grid drops what is dragged, if the screen accepts it there. */
  const dropOver = (event: DragEvent<HTMLElement>): Drop | undefined => {
    const cell = event.target instanceof Element ? event.target.closest("td[data-row]") : null;
    const at = positionOf(cell);
    if (
      dropping === undefined ||
      dragged.current === undefined ||
      !event.dataTransfer.types.includes(DRAGGED_ROWS) ||
      cell === null ||
      at === undefined
    ) {
      return undefined;
    }
    const beside = dropBeside(cell, event.clientY, at.row, rows.length);
    const target = rows[beside.index];
    return target !== undefined && dropping.accepts(carried(), target, beside.place)
      ? beside
      : undefined;
  };
  const body = {
    onClick: (event: MouseEvent<HTMLElement>) => {
      const index = offered ? handleOf(event.target) : undefined;
      if (index !== undefined) {
        select(index, event.shiftKey);
      }
    },
    onDragStart: (event: DragEvent<HTMLElement>) => {
      const index = offered ? handleOf(event.target) : undefined;
      if (index === undefined) {
        return;
      }
      if (!isSelected(index)) {
        select(index, false);
      }
      dragged.current = acted(index).map(keyOf);
      event.dataTransfer.effectAllowed = "move";
      event.dataTransfer.setData(DRAGGED_ROWS, dragged.current.join("\n"));
    },
    onDragOver: (event: DragEvent<HTMLElement>) => {
      const next = dropOver(event);
      if (next !== undefined) {
        event.preventDefault();
        event.dataTransfer.dropEffect = "move";
      }
      if (next?.index !== drop?.index || next?.place !== drop?.place) {
        setDrop(next);
      }
    },
    onDragLeave: (event: DragEvent<HTMLElement>) => {
      const { relatedTarget } = event;
      if (!(relatedTarget instanceof Node) || !event.currentTarget.contains(relatedTarget)) {
        setDrop(undefined);
      }
    },
    onDrop: (event: DragEvent<HTMLElement>) => {
      const at = dropOver(event);
      const target = at === undefined ? undefined : rows[at.index];
      if (dropping !== undefined && at !== undefined && target !== undefined) {
        event.preventDefault();
        dropping.drop(carried(), target, at.place);
      }
      clear();
    },
    onDragEnd: clear,
  };
  return {
    offered,
    /** Whether the row at an index is selected; none where the grid selects nothing. */
    selected: (index: number): boolean | undefined => (offered ? isSelected(index) : undefined),
    /** Where what is dragged would drop beside the row at an index, if there. */
    dropAt: (index: number): DropPlace | undefined =>
      drop?.index === index ? drop.place : undefined,
    acted,
    /** How many rows are selected; none where the grid selects nothing. */
    count: offered ? (bounds === undefined ? 0 : bounds[1] - bounds[0] + 1) : undefined,
    /** Whether the grid says it takes several rows: where it selects. */
    multiselectable: offered ? true : undefined,
    onKeyDown,
    body,
  };
}

/** The selection of a grid, as `useRowSelection` gives it. */
export type RowSelection<Row> = ReturnType<typeof useRowSelection<Row>>;

/** The keys of a handle, as `aria-keyshortcuts` names them. */
const HANDLE_KEYS = "Space Shift+ArrowUp Shift+ArrowDown Escape";

/** The classes of a row by what is dropped beside it: a line before or after it, or its shade. */
const DROP_CLASSES: Readonly<Record<DropPlace, string>> = {
  before:
    "[&>td:not(.sticky)]:relative [&>td]:before:pointer-events-none [&>td]:before:absolute [&>td]:before:inset-x-0 [&>td]:before:top-0 [&>td]:before:h-0.5 [&>td]:before:bg-primary",
  after:
    "[&>td:not(.sticky)]:relative [&>td]:before:pointer-events-none [&>td]:before:absolute [&>td]:before:inset-x-0 [&>td]:before:bottom-0 [&>td]:before:h-0.5 [&>td]:before:bg-primary",
  into: "[&>td]:bg-accent [&>td]:font-semibold",
};

/**
 * The attributes and the classes of a row of a grid that selects: its cells tinted, but the computed
 * ones — which open a dialog —, which keep the shade that tells them computed (WF-IHM-0030); and
 * what is dropped beside it, if anything (`data-drop`).
 */
export function selectedRow(selected: boolean | undefined, drop: DropPlace | undefined) {
  return {
    "aria-selected": selected,
    "data-drop": drop,
    className: cn(
      selected === true ? "[&>td:not([aria-haspopup=dialog])]:bg-accent" : null,
      drop === undefined ? null : DROP_CLASSES[drop],
    ),
  };
}

/** The classes of the handle of a row, narrower in its padding for its mark and its number. */
const HANDLE_CELL =
  "overflow-hidden bg-background px-1 text-muted-foreground outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-inset";

/** A cell that tells no key of the folding. */
const NO_FOLD = { folds: false, keys: undefined };

/**
 * The handle of a row, in the cell of its number: a cell of the grid like the others, reached by the
 * arrows, which selects and drags its row, is named by the number of its row and described by how
 * it selects and moves (`SelectionNotes`); a mark grips it, another where its row is selected.
 */
export function HandleCell({
  position,
  state,
  menu,
  pinning,
  number,
  selected,
  name,
  hint,
}: {
  readonly position: CellPosition;
  readonly state: CellState;
  /** Whether the cells have a menu, which they announce. */
  readonly menu: boolean;
  readonly pinning: { readonly className: string; readonly left: number | undefined };
  readonly number: number | undefined;
  readonly selected: boolean;
  readonly name: (number: number) => string;
  readonly hint: string;
}) {
  const Mark = selected ? Check : GripVertical;
  const keys = [...cellKeys(menu, NO_FOLD, "", undefined), HANDLE_KEYS];
  return (
    <TableCell
      {...cellAttributes(position, state, false, false, keys)}
      draggable
      aria-label={name(number ?? 0)}
      aria-describedby={hint}
      style={{ left: pinning.left }}
      className={cn(HANDLE_CELL, pinning.className)}
    >
      <span className="flex cursor-grab items-center justify-end gap-0.5 select-none">
        <Mark aria-hidden="true" className="size-2.5 shrink-0" />
        {number}
      </span>
    </TableCell>
  );
}

/**
 * What a grid that selects says once: how to select and move with its handles, which each handle
 * names as its description, and how many rows are selected, in a status.
 */
export function SelectionNotes({
  hint,
  count,
}: {
  readonly hint: string;
  readonly count: number | undefined;
}) {
  const t = useTranslations("grid.selection");
  if (count === undefined) {
    return null;
  }
  return (
    <>
      <p id={hint} hidden>
        {t("hint")}
      </p>
      <p role="status" aria-live="polite" className="sr-only">
        {count === 0 ? null : t("count", { count })}
      </p>
    </>
  );
}
