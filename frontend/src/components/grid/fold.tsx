// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The tree of a dense grid, folded and unfolded (WF-PLA-0080, WF-PLA-0090, EP-02/L40): the
 * planning, the estimate and the remaining to commit, whose rows say which row they are under
 * (`GridTree.parent`). A row under which the answer holds others — a summary over its tasks, a task
 * over its lines — folds them: they leave the rows of the grid, those it renders, numbers in the
 * order of the rows and the keyboard moves through, as they leave the Gantt, a column of the same
 * grid — folded in the one, a summary is folded in the other.
 *
 * Nothing is asked of the server, and nothing is sent to it: what is folded is kept in the storage
 * of the session of the tab (`sessionStorage`), by grid and by revision, the identities of the
 * rows folded — a row the answer no longer holds keeps its fold for a reading that brings it back.
 * The server renders the tree unfolded, and the browser folds it once hydrated: the storage is the
 * browser's. Kept with care, as the tasks a tab follows are (`tasks/storage.ts`): read back only
 * when it has the shape written, and kept in memory alone when the browser refuses the storage.
 *
 * A search, or a filter, that retains a row folded away unfolds the rows above it (WF-PLA-0080 :
 * « La recherche sur un libellé ne laisse voir que les tâches correspondantes et leurs parents »):
 * the answer of a reading so narrowed holds the rows it retains and the rows above them, and each
 * of those under which it holds others unfolds — once for each search or filter, which the user
 * may fold again.
 */
"use client";

import { ChevronDown, ChevronRight } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  createContext,
  type CSSProperties,
  type KeyboardEvent,
  type MouseEvent,
  type RefObject,
  use,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useSyncExternalStore,
} from "react";

import { ContextMenuItem } from "@/components/ui/context-menu";
import { cn } from "@/components/ui/utils";

import type { GridTree } from "./columns";
import { type CellPosition, type Cursor, HEADER_ROW, positionOf } from "./grid-keyboard";
import type { GridOutline } from "./grid-toolbar";

/** The prefix of the keys of the storage of the tab under which a grid keeps its folds. */
export const FOLD_STORAGE_PREFIX = "wf_fold:";

/** What a grid keeps of its tree: the rows folded, and the narrowing last unfolded for. */
interface FoldState {
  readonly collapsed: ReadonlySet<string>;
  /** The search and the filters whose rows were last unfolded; empty for a reading not narrowed. */
  readonly revealed: string;
}

/** Nothing folded: the tree as the server renders it. */
const UNFOLDED: FoldState = { collapsed: new Set(), revealed: "" };

/** What is kept in memory alone, by key, when the browser refuses its storage. */
const memory = new Map<string, string>();

/** The last state read of each key, with what it was read from: the same object while unchanged. */
const read = new Map<string, { readonly raw: string | null; readonly state: FoldState }>();

/** Who listens to what the grids keep. */
const listeners = new Set<() => void>();

/**
 * What a grid keeps under a key, if anything: in memory first — what the storage refused, newer than
 * what it held before —, in the storage of the tab otherwise.
 */
function rawOf(key: string): string | null {
  const kept = memory.get(key);
  if (kept !== undefined) {
    return kept;
  }
  try {
    return window.sessionStorage.getItem(FOLD_STORAGE_PREFIX + key);
  } catch {
    return null;
  }
}

/** A state read back, when it has the shape written; nothing folded otherwise. */
function parsed(raw: string | null): FoldState {
  try {
    const value: unknown = JSON.parse(raw ?? "null");
    if (typeof value !== "object" || value === null) {
      return UNFOLDED;
    }
    const { collapsed, revealed } = value as { collapsed?: unknown; revealed?: unknown };
    return Array.isArray(collapsed) &&
      collapsed.every((key) => typeof key === "string") &&
      typeof revealed === "string"
      ? { collapsed: new Set(collapsed), revealed }
      : UNFOLDED;
  } catch {
    return UNFOLDED;
  }
}

/** What a grid keeps of its tree, under its key: the same object as long as it does not change. */
function foldState(key: string): FoldState {
  const raw = rawOf(key);
  const before = read.get(key);
  if (before?.raw === raw) {
    return before.state;
  }
  const state = parsed(raw);
  read.set(key, { raw, state });
  return state;
}

/** Keep what a grid folded, and tell those who listen. */
function keep(key: string, state: FoldState): void {
  const raw = JSON.stringify({ collapsed: [...state.collapsed], revealed: state.revealed });
  try {
    window.sessionStorage.setItem(FOLD_STORAGE_PREFIX + key, raw);
    memory.delete(key);
  } catch {
    // Refused — a quota, a private window —: the fold is kept in memory, a reload loses it.
    memory.set(key, raw);
  }
  for (const listener of listeners) {
    listener();
  }
}

/** Listen to what the grids keep. */
function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Where a row stands in the tree, as a reader of the screen is told it. */
export interface TreePlace {
  readonly level: number;
  /** Its place among the rows under the same row, from 1. */
  readonly position: number;
  /** How many rows are under the same row. */
  readonly siblings: number;
}

/** The tree of an answer: who is under whom, by the identities of the rows. */
export interface TreeIndex {
  /** The rows under which the answer holds others: those that fold. */
  readonly parents: ReadonlySet<string>;
  /** The row each row is under, when the answer holds it. */
  readonly parentOf: ReadonlyMap<string, string>;
  /** The level of each row that folds. */
  readonly levelOf: ReadonlyMap<string, number>;
  /** Where each row stands. */
  readonly places: ReadonlyMap<string, TreePlace>;
  /** The deepest level of a row that folds; 0 when none does. */
  readonly deepest: number;
}

/** The tree of the rows of an answer, read from the parent each row names. */
export function treeIndex<Row>(
  rows: readonly Row[],
  rowKey: (row: Row) => string,
  tree: GridTree<Row> | undefined,
): TreeIndex {
  const parent = tree?.parent;
  const keys = new Set(rows.map((row) => rowKey(row)));
  const parentOf = new Map<string, string>();
  const children = new Map<string | null, string[]>();
  for (const row of rows) {
    const key = rowKey(row);
    const above = parent?.(row) ?? null;
    const held = above !== null && keys.has(above) ? above : null;
    if (held !== null) {
      parentOf.set(key, held);
    }
    const under = children.get(held) ?? [];
    under.push(key);
    children.set(held, under);
  }
  const levels = new Map(rows.map((row) => [rowKey(row), tree?.level(row) ?? 1]));
  const levelOf = new Map<string, number>();
  const places = new Map<string, TreePlace>();
  for (const [above, under] of children) {
    if (above !== null) {
      levelOf.set(above, levels.get(above) ?? 1);
    }
    under.forEach((key, at) => {
      places.set(key, { level: levels.get(key) ?? 1, position: at + 1, siblings: under.length });
    });
  }
  return {
    parents: new Set(levelOf.keys()),
    parentOf,
    levelOf,
    places,
    deepest: Math.max(0, ...levelOf.values()),
  };
}

/** The rows that stay once some are folded: those under no row folded, in the order of the answer. */
export function unfoldedRows<Row>(
  rows: readonly Row[],
  rowKey: (row: Row) => string,
  index: TreeIndex,
  collapsed: ReadonlySet<string>,
): readonly Row[] {
  if (collapsed.size === 0) {
    return rows;
  }
  const hidden = new Map<string, boolean>();
  const hiddenUnder = (key: string): boolean => {
    const known = hidden.get(key);
    if (known !== undefined) {
      return known;
    }
    const above = index.parentOf.get(key);
    const result = above !== undefined && (collapsed.has(above) || hiddenUnder(above));
    hidden.set(key, result);
    return result;
  };
  return rows.filter((row) => !hiddenUnder(rowKey(row)));
}

/** The rows folded, a row folded or unfolded — the other way round from now, when not said. */
export function toggled(
  collapsed: ReadonlySet<string>,
  key: string,
  expand: boolean = collapsed.has(key),
): ReadonlySet<string> {
  const next = new Set(collapsed);
  if (expand) {
    next.delete(key);
  } else {
    next.add(key);
  }
  return next;
}

/** The rows folded to show the tree down to a level: each row that folds, from that level down. */
export function foldedTo(index: TreeIndex, level: number): ReadonlySet<string> {
  return new Set([...index.levelOf].filter(([, at]) => at >= level).map(([key]) => key));
}

/** The rows folded, but those of an answer that fold: what a narrowed reading unfolds. */
function revealed(collapsed: ReadonlySet<string>, index: TreeIndex): ReadonlySet<string> {
  return new Set([...collapsed].filter((key) => !index.parents.has(key)));
}

/** What a grid folds by. */
export interface GridFoldOptions<Row> {
  readonly tree: GridTree<Row> | undefined;
  readonly rowKey: (row: Row) => string;
  /** The rows of the answer, as its writes left them, in its order. */
  readonly rows: readonly Row[];
  /** The key of the grid, under which it keeps its folds. */
  readonly grid: string;
  /** What the grid keeps its folds for besides itself: the revision it reads. */
  readonly scope: string | undefined;
  /**
   * What the reading asked of the server besides its fields and its sort — the search, the filters —,
   * as it was sent; none, or nothing in it, for a reading not narrowed.
   */
  readonly narrowing: Readonly<Record<string, unknown>> | undefined;
}

/** The tree of a grid, as it is folded, and how to fold it. */
export interface GridFold<Row> {
  /** Whether the tree of the grid folds: its rows name their parents. */
  readonly enabled: boolean;
  /** The rows that stay, in the order of the answer. */
  readonly shown: readonly Row[];
  readonly index: TreeIndex;
  readonly collapsed: ReadonlySet<string>;
  /** The rows that would stay, folded otherwise. */
  readonly shownWith: (collapsed: ReadonlySet<string>) => readonly Row[];
  /** Fold the tree otherwise, and keep it. */
  readonly set: (collapsed: ReadonlySet<string>) => void;
  /**
   * Whether a row folded away is among the rows a block of rows fills from a row, in the order of
   * the answer — the row itself, then those after it.
   */
  readonly foldedFrom: (row: Row, count: number) => boolean;
}

/** The key of what a reading is narrowed by: its entries said, in the order of their names. */
function narrowingKey(narrowing: Readonly<Record<string, unknown>> | undefined): string {
  const said = Object.entries(narrowing ?? {})
    .filter(([, value]) => value !== undefined)
    .sort(([a], [b]) => (a < b ? -1 : 1));
  return said.length === 0 ? "" : JSON.stringify(said);
}

/**
 * The tree of a grid, folded as the session keeps it — unfolded on the server, and until the page
 * is hydrated —, the rows a narrowed reading retains unfolded.
 */
export function useGridFold<Row>({
  tree,
  rowKey,
  rows,
  grid,
  scope,
  narrowing: by,
}: GridFoldOptions<Row>): GridFold<Row> {
  const storageKey = `${grid}:${scope ?? ""}`;
  const enabled = tree?.parent !== undefined;
  const narrowing = narrowingKey(by);
  const index = useMemo(() => treeIndex(rows, rowKey, tree), [rows, rowKey, tree]);
  const stored = useSyncExternalStore(
    subscribe,
    () => (enabled ? foldState(storageKey) : UNFOLDED),
    () => UNFOLDED,
  );
  // A narrowing not unfolded for yet shows the rows it retains at once, before it is kept.
  const pending = narrowing !== "" && stored.revealed !== narrowing;
  const collapsed = pending ? revealed(stored.collapsed, index) : stored.collapsed;
  useEffect(() => {
    // What the storage holds now, never what the render read: hydrated, it read nothing.
    const now = enabled ? foldState(storageKey) : undefined;
    if (now === undefined || now.revealed === narrowing) {
      return;
    }
    keep(storageKey, {
      collapsed: narrowing === "" ? now.collapsed : revealed(now.collapsed, index),
      revealed: narrowing,
    });
  }, [enabled, storageKey, narrowing, index]);
  const shown = useMemo(
    () => unfoldedRows(rows, rowKey, index, collapsed),
    [rows, rowKey, index, collapsed],
  );
  return {
    enabled,
    shown,
    index,
    collapsed,
    shownWith: (next) => unfoldedRows(rows, rowKey, index, next),
    set: (next) => {
      keep(storageKey, { collapsed: next, revealed: narrowing });
    },
    foldedFrom: (row, count) => {
      if (shown.length === rows.length) {
        return false;
      }
      const stay = new Set(shown.map((each) => rowKey(each)));
      const from = rows.indexOf(row);
      return rows.slice(from, from + count).some((each) => !stay.has(rowKey(each)));
    },
  };
}

/**
 * Where the cursor goes once the tree is folded otherwise: the row it was on, or the nearest row
 * above it that stays — by its index among the rows that stay —; none for a row the answer does not
 * hold.
 */
export function rowAfterFold<Row>(
  next: readonly Row[],
  rowKey: (row: Row) => string,
  index: TreeIndex,
  key: string | undefined,
): number | undefined {
  const at = new Map(next.map((row, position) => [rowKey(row), position]));
  for (let each = key; each !== undefined; each = index.parentOf.get(each)) {
    const found = at.get(each);
    if (found !== undefined) {
      return found;
    }
  }
  return undefined;
}

/** What the folding of a grid does at a key: fold the row, unfold it, or unfold the whole tree. */
export type FoldCommand = "collapse" | "expand" | "expandAll";

/** Each command of the folding, and the characters of its keys. */
const FOLD_CHARACTERS: readonly (readonly [FoldCommand, readonly string[]])[] = [
  ["collapse", ["-", "_"]],
  ["expand", ["+", "="]],
  ["expandAll", ["*"]],
];

/** The keys of the numeric keypad, which type the same character whatever the layout. */
const KEYPAD: Readonly<Record<string, FoldCommand>> = {
  NumpadSubtract: "collapse",
  NumpadAdd: "expand",
  NumpadMultiply: "expandAll",
};

/** The command a character asks for, if any. */
function commandOf(character: string | undefined): FoldCommand | undefined {
  return FOLD_CHARACTERS.find(([, characters]) => characters.includes(character ?? ""))?.[0];
}

/** What the browser says of the layout of the keyboard: the character of each key, by its place. */
type KeyboardLayout = ReadonlyMap<string, string>;

/** The layout of the keyboard, once the browser has told it — those of the Keyboard API alone. */
let layout: KeyboardLayout | undefined;

/** The Keyboard API, which some browsers offer. */
interface KeyboardApi {
  readonly keyboard?: { readonly getLayoutMap?: () => Promise<KeyboardLayout> };
}

/**
 * Ask the browser the layout of the keyboard, where it tells it: kept for the keys to come — none
 * where it does not.
 */
function readLayout(): void {
  const api = (navigator as Navigator & KeyboardApi).keyboard;
  layout = undefined;
  void api
    ?.getLayoutMap?.()
    .then((map) => {
      layout = map;
    })
    .catch(() => undefined);
}

/**
 * The folding a key asks for, as in Microsoft Project: Alt and minus folds, Alt and plus unfolds,
 * Alt and * unfolds the whole tree — Shift or not, whichever the layout asks to type the
 * character: on an AZERTY keyboard, minus and * come without it. The character is the one the key
 * typed, and, when it is none of the folding, the one the key bears in the layout the browser tells
 * (`getLayoutMap`) — Option on a Mac types another character than the key bears. Never by the place
 * alone, which bears another character on another layout. The numeric keypad types the same
 * characters whatever the layout. Without the layout — Safari, Firefox on a Mac —, Option with a key
 * types another character, which nothing reads: the menu of the cells folds there (`CellMenu`).
 */
export function foldShortcut(
  event: {
    readonly key: string;
    readonly code: string;
    readonly altKey: boolean;
    readonly ctrlKey: boolean;
    readonly metaKey: boolean;
    readonly getModifierState: (key: "AltGraph") => boolean;
  },
  told: KeyboardLayout | undefined,
): FoldCommand | undefined {
  // AltGr aside — which Windows reports as Ctrl and Alt together —: it types a character.
  const altGraph = event.getModifierState("AltGraph");
  if (!event.altKey || altGraph || event.ctrlKey || event.metaKey) {
    return undefined;
  }
  const keypad = KEYPAD[event.code];
  if (keypad !== undefined) {
    return keypad;
  }
  return commandOf(event.key) ?? commandOf(told?.get(event.code));
}

/**
 * How far the keys of the folding reach in this browser: all of them off a Mac; on a Mac, minus and
 * plus where the browser tells the layout — Option and 8 types no * there —, none where it does not
 * (Safari, Firefox), where the menu of the cells folds alone.
 */
export type FoldReach = "all" | "row" | "none";

/** Whether the browser runs on a Mac, whose Option types another character than the key bears. */
function onMac(): boolean {
  const nav = navigator as Navigator & { readonly userAgentData?: { readonly platform?: string } };
  return /mac|iphone|ipad/i.test(nav.userAgentData?.platform ?? nav.userAgent);
}

/** How far the keys of the folding reach, decided once for the browser. */
function reachNow(): FoldReach {
  if (!onMac()) {
    return "all";
  }
  return (navigator as Navigator & KeyboardApi).keyboard?.getLayoutMap === undefined
    ? "none"
    : "row";
}

/** A store that never changes: the browser stays what it is. */
function unchanging(): () => void {
  return () => undefined;
}

/**
 * How far the keys of the folding reach, read once the page is hydrated — none on the server, which
 * does not know the browser, nor while hydrating, which must render what the server did.
 */
export function useFoldReach(): FoldReach {
  return useSyncExternalStore(unchanging, reachNow, () => "none");
}

/** The keys of the folding of a row, as `aria-keyshortcuts` names them, as far as they reach. */
export const FOLD_KEYS: Readonly<Record<FoldReach, string | undefined>> = {
  all: "Alt+- Alt+Plus Alt+*",
  row: "Alt+- Alt+Plus",
  none: undefined,
};

/** What folds the tree of a grid: its fold, its active cell, the element that scrolls it. */
export interface FoldCommandsOptions<Row> {
  readonly fold: GridFold<Row>;
  readonly rowKey: (row: Row) => string;
  readonly cursor: Cursor;
  readonly scroller: RefObject<HTMLElement | null>;
  /** Focus a cell, once rendered, brought into view. */
  readonly focusAt: (at: CellPosition) => void;
  /** The label of a row, which the menu names the row it folds by. */
  readonly labelOf: (row: Row) => string;
}

/** How a grid folds its tree: what its cells read, its keys, its bar; nothing for a grid no tree. */
export interface FoldCommands {
  /** The role of the grid: a tree grid, when its tree folds. */
  readonly role: "grid" | "treegrid";
  readonly view: FoldView | undefined;
  /** Fold on the keys of the folding pressed on a cell of the body: whether the key was one. */
  readonly onKeyDown: (event: KeyboardEvent<HTMLElement>) => boolean;
  readonly outline: GridOutline | undefined;
  /** The folding the menu of the cells offers. */
  readonly menu: CellFolding | undefined;
}

/**
 * The folding the menu of a cell offers (`CellMenu`), which works in every browser, where the keys
 * of the folding do not (`foldShortcut`): fold or unfold the row of the cell, unfold the whole tree.
 */
export interface CellFolding {
  /**
   * Whether the row of a cell may be folded — or the row above it, named by its label — and
   * unfolded; neither without a cell — the empty row of a grid.
   */
  readonly offers: (at: CellPosition | undefined) => {
    readonly collapse: { readonly above: string | undefined } | undefined;
    readonly expand: boolean;
  };
  readonly run: (command: FoldCommand, at: CellPosition | undefined) => void;
}

/**
 * Fold the tree of a grid from its cells, its keys and its bar. The active cell stays on its row —
 * or goes to the row it is folded under —, by its index among the rows that stay; the focus goes
 * with it when the grid held it, or when a row was folded from a cell, once the rows are rendered.
 */
export function useFoldCommands<Row>({
  fold,
  rowKey,
  cursor,
  scroller,
  focusAt,
  labelOf,
}: FoldCommandsOptions<Row>): FoldCommands {
  useEffect(() => {
    readLayout();
  }, []);
  const refocus = useRef<CellPosition>(undefined);
  useLayoutEffect(() => {
    const at = refocus.current;
    if (at !== undefined) {
      refocus.current = undefined;
      focusAt(at);
    }
  });
  const { shown, index, collapsed } = fold;
  const refold = (
    next: ReadonlySet<string>,
    from?: { readonly key: string; readonly column: string | undefined },
  ) => {
    const active = cursor.active.row === HEADER_ROW ? undefined : shown[cursor.active.row];
    const key = from?.key ?? (active === undefined ? undefined : rowKey(active));
    const row = rowAfterFold(fold.shownWith(next), rowKey, index, key);
    const holding = from !== undefined || scroller.current?.contains(document.activeElement);
    fold.set(next);
    if (row !== undefined) {
      const at = { row, column: from?.column ?? cursor.active.column };
      cursor.set(at);
      refocus.current = holding === true ? at : undefined;
    }
  };
  // The row a command folds or unfolds from the row of a cell — the row above it, folded from a
  // row under which nothing folds —, when it changes it.
  const targetOf = (command: FoldCommand, at: CellPosition): string | undefined => {
    const row = shown[at.row];
    const own = row === undefined ? undefined : rowKey(row);
    const key =
      own !== undefined && command === "collapse" && !index.parents.has(own)
        ? index.parentOf.get(own)
        : own;
    const folds = key !== undefined && index.parents.has(key);
    return folds && collapsed.has(key) === (command === "expand") ? key : undefined;
  };
  const run = (command: FoldCommand, at: CellPosition | undefined) => {
    if (command === "expandAll") {
      refold(new Set());
      return;
    }
    const key = at === undefined ? undefined : targetOf(command, at);
    if (key !== undefined && at !== undefined) {
      refold(toggled(collapsed, key, command === "expand"), { key, column: at.column });
    }
  };
  // The label of the row a fold from a cell folds, when it is another row than the cell's.
  const aboveOf = (at: CellPosition, key: string): string | undefined => {
    const row = shown[at.row];
    const target = shown.find((each) => rowKey(each) === key);
    return row === undefined || rowKey(row) === key || target === undefined
      ? undefined
      : labelOf(target);
  };
  // The keys, on a cell of the body.
  const onKeyDown = (event: KeyboardEvent<HTMLElement>): boolean => {
    const command = fold.enabled ? foldShortcut(event, layout) : undefined;
    const at = positionOf(event.target);
    if (command === undefined || at === undefined || shown[at.row] === undefined) {
      return false;
    }
    run(command, at);
    return true;
  };
  if (!fold.enabled) {
    return { role: "grid", view: undefined, onKeyDown, outline: undefined, menu: undefined };
  }
  return {
    role: "treegrid",
    view: {
      expanded: (key) => (index.parents.has(key) ? !collapsed.has(key) : undefined),
      place: (key) => index.places.get(key),
      toggle: (key, column) => {
        refold(toggled(collapsed, key), { key, column });
      },
    },
    onKeyDown,
    menu: {
      offers: (at) => {
        const key = at === undefined ? undefined : targetOf("collapse", at);
        return {
          collapse: key === undefined || at === undefined ? undefined : { above: aboveOf(at, key) },
          expand: at !== undefined && targetOf("expand", at) !== undefined,
        };
      },
      run,
    },
    outline: {
      levels: index.deepest,
      expandAll: () => {
        refold(new Set());
      },
      collapseTo: (level) => {
        refold(foldedTo(index, level));
      },
    },
  };
}

/**
 * The keys of a command of the folding the menu of a cell tells, as far as they reach: minus and
 * plus where the keys of a row do, * off a Mac alone.
 */
const MENU_KEYS: Readonly<Record<FoldCommand, Readonly<Record<FoldReach, string | undefined>>>> = {
  collapse: { all: "Alt+-", row: "Alt+-", none: undefined },
  expand: { all: "Alt+Plus", row: "Alt+Plus", none: undefined },
  expandAll: { all: "Alt+*", row: undefined, none: undefined },
};

/**
 * The folding in the menu of a cell (`CellMenu`): fold the row of the cell — or the row above it,
 * from a row under which nothing folds, named by its label —, unfold it, each where it changes
 * something, and unfold the whole tree, offered on any cell and without one — the empty row of a
 * grid —, so that the menu is never empty. It works wherever the keys of the folding do not:
 * Option on a Mac, without the layout of the keyboard, types a character that names no command.
 */
export function FoldMenuItems({
  folding,
  at,
  onRun,
}: {
  readonly folding: CellFolding;
  /** The cell the menu opened on, if it opened on one. */
  readonly at: CellPosition | undefined;
  /** Told once a command ran. */
  readonly onRun: () => void;
}) {
  const t = useTranslations("grid.fold");
  const reach = useFoldReach();
  const { collapse, expand } = folding.offers(at);
  const collapseLabel =
    collapse?.above === undefined
      ? t("collapseRow")
      : t("collapseAbove", { label: collapse.above });
  const items: readonly (readonly [FoldCommand, string | undefined])[] = [
    ["collapse", collapse === undefined ? undefined : collapseLabel],
    ["expand", expand ? t("expandRow") : undefined],
    ["expandAll", t("expandAll")],
  ];
  return items.map(([command, label]) =>
    label === undefined ? null : (
      <ContextMenuItem
        key={command}
        aria-keyshortcuts={MENU_KEYS[command][reach]}
        onSelect={() => {
          onRun();
          folding.run(command, at);
        }}
      >
        {label}
      </ContextMenuItem>
    ),
  );
}

/** What the cells of a grid read of its tree, by the identity of their row. */
export interface FoldView {
  /** Whether the row is unfolded; none for a row under which the answer holds nothing. */
  readonly expanded: (key: string) => boolean | undefined;
  /** Where the row stands in the tree. */
  readonly place: (key: string) => TreePlace | undefined;
  /**
   * Fold or unfold the row, from the cell of a column, which becomes the active one — the column of
   * the active cell, when the cell is not told.
   */
  readonly toggle: (key: string, column: string | undefined) => void;
}

/** The tree of the grid around, when it folds. */
export const FoldContext = createContext<FoldView | undefined>(undefined);

/** Where the row of a cell stands in the tree of its grid, and whether it is unfolded. */
export function useTreeRow(
  key: string,
): (TreePlace & { readonly expanded: boolean | undefined }) | undefined {
  const fold = use(FoldContext);
  const place = fold?.place(key);
  return place === undefined ? undefined : { ...place, expanded: fold?.expanded(key) };
}

/**
 * The button that folds or unfolds a row, in its label — and in its bar of the Gantt —: out of the
 * order of tabulation, the grid being one stop, whose keys fold the active row. A click makes its
 * cell the active one, the focus on it; a double click does not enter the cell. A row under which
 * nothing folds has none, its place kept in a label, so that the labels stay aligned by level.
 */
export function FoldToggle({
  rowKey,
  placeholder,
  className,
  style,
}: {
  readonly rowKey: string;
  /** Whether a row that does not fold keeps the place of the button. */
  readonly placeholder?: boolean;
  readonly className?: string;
  readonly style?: CSSProperties;
}) {
  const t = useTranslations("grid.fold");
  const fold = use(FoldContext);
  const expanded = fold?.expanded(rowKey);
  if (fold === undefined) {
    return null;
  }
  if (expanded === undefined) {
    return placeholder === true ? <span aria-hidden="true" className="size-4 shrink-0" /> : null;
  }
  const Icon = expanded ? ChevronDown : ChevronRight;
  const toggle = (event: MouseEvent<HTMLButtonElement>) => {
    event.stopPropagation();
    const column = event.currentTarget.closest<HTMLElement>("td[data-column]")?.dataset.column;
    fold.toggle(rowKey, column);
  };
  return (
    <button
      type="button"
      tabIndex={-1}
      aria-label={expanded ? t("collapse") : t("expand")}
      onMouseDown={(event) => {
        // The focus stays on the grid: the click gives it to the cell.
        event.preventDefault();
      }}
      onClick={toggle}
      onDoubleClick={(event) => {
        event.stopPropagation();
      }}
      style={style}
      className={cn(
        "inline-flex size-4 shrink-0 items-center justify-center rounded-sm text-muted-foreground hover:bg-accent hover:text-foreground",
        className,
      )}
    >
      <Icon aria-hidden="true" className="size-3.5" />
    </button>
  );
}
