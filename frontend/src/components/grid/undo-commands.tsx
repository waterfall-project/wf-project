// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Undo and redo of the entries of a revision (WF-IHM-0110), placed where they will act — in the
 * bar of a grid that enters a revision in progress, in the menu of its cells, and by Ctrl+Z and
 * Ctrl+Shift+Z on the grid — but not wired: the server keeps no history of the entries yet, and
 * EP-06 wires them on `undoLastChange` and `redoLastUndo`, the undoing being the server's, never a
 * stack in the browser (WF-ARC-0070). Until then they are unavailable, and say why: the buttons and
 * the entries of the menu are reached by the keyboard, marked `aria-disabled` and described by the
 * reason, and the shortcut tells it in a region announced.
 *
 * Only a grid whose revision in progress is entered by its command `edit_*` offers them: none
 * undoes a marking, an import applied or the exclusion of a line of actual cost.
 *
 * The shortcut is taken in the grid and its bar, never in a menu or a dialog they open, and never
 * from a field being entered: Ctrl+Z in the editor of a cell, or in the search, stays the
 * browser's, which undoes what was typed in it.
 */
"use client";

import { Redo2, Undo2 } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  type KeyboardEvent,
  type MouseEvent,
  type ReactElement,
  useId,
  useRef,
  useState,
} from "react";

import { Button } from "@/components/ui/button";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuLabel,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import { cn } from "@/components/ui/utils";

/** The two commands. */
export type UndoCommand = "undo" | "redo";

const COMMANDS: readonly UndoCommand[] = ["undo", "redo"];

/** The shortcuts of each command, as `aria-keyshortcuts` names them: Ctrl, or Cmd on a Mac. */
const KEYS: Readonly<Record<UndoCommand, string>> = {
  undo: "Control+Z Meta+Z",
  redo: "Control+Shift+Z Meta+Shift+Z",
};

const UNAVAILABLE = "aria-disabled:cursor-not-allowed aria-disabled:opacity-50";

/** The command a key asks for: Ctrl+Z undoes, Ctrl+Shift+Z redoes — Cmd on a Mac. */
export function undoShortcut(event: {
  readonly key: string;
  readonly ctrlKey: boolean;
  readonly metaKey: boolean;
  readonly altKey: boolean;
  readonly shiftKey: boolean;
}): UndoCommand | undefined {
  // Alt aside: AltGr, which Windows reports as Ctrl and Alt together, types a character.
  if (!(event.ctrlKey || event.metaKey) || event.altKey || event.key.toLowerCase() !== "z") {
    return undefined;
  }
  return event.shiftKey ? "redo" : "undo";
}

/** Whether an element is a field being entered, whose own undo is the browser's. */
function entering(target: EventTarget): boolean {
  return (
    target instanceof HTMLElement &&
    (target.isContentEditable || ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName))
  );
}

/** What a grid does of the shortcut, and what it last told of it. */
export interface UndoShortcut {
  /** The key down on the grid, which the shortcut takes, a field being entered aside. */
  readonly onKeyDown: (event: KeyboardEvent<HTMLElement>) => void;
  /** The command the shortcut last asked, told unavailable, and how many times it was asked. */
  readonly told: { readonly command: UndoCommand; readonly count: number } | undefined;
}

/** Take Ctrl+Z and Ctrl+Shift+Z on a grid that offers the commands; none, and nothing is taken. */
export function useUndoShortcut(offered: boolean | undefined): UndoShortcut {
  const [told, setTold] = useState<UndoShortcut["told"]>();
  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    const command = undoShortcut(event);
    // Only what was pressed in the grid itself: a menu or a dialog it opened is drawn elsewhere.
    if (
      offered !== true ||
      command === undefined ||
      event.defaultPrevented ||
      !(event.target instanceof Node) ||
      !event.currentTarget.contains(event.target) ||
      entering(event.target)
    ) {
      return;
    }
    event.preventDefault();
    setTold((before) => ({ command, count: (before?.count ?? 0) + 1 }));
  };
  return { onKeyDown, told };
}

/**
 * Render the region that tells the shortcut pressed unavailable, present before it is, in a grid
 * that offers the commands; none otherwise.
 */
export function UndoAnnouncer({
  offered,
  told,
}: {
  readonly offered: boolean | undefined;
  readonly told: UndoShortcut["told"];
}) {
  const t = useTranslations("grid.undo");
  if (offered !== true) {
    return null;
  }
  return (
    <div role="status" aria-live="polite" className="sr-only">
      {/* A new node each time, so that the same command pressed again is heard again. */}
      {told === undefined ? null : <p key={told.count}>{t(`told.${told.command}`)}</p>}
    </div>
  );
}

/** Render the commands in the bar of a grid: their buttons, and why they wait. */
export function UndoCommands() {
  const t = useTranslations("grid.undo");
  const reason = useId();
  return (
    <div className="flex items-center gap-1">
      {COMMANDS.map((command) => (
        <Button
          key={command}
          type="button"
          variant="outline"
          size="icon"
          aria-label={t(command)}
          aria-disabled
          aria-describedby={reason}
          aria-keyshortcuts={KEYS[command]}
          className={cn("size-7", UNAVAILABLE)}
        >
          {command === "undo" ? <Undo2 aria-hidden="true" /> : <Redo2 aria-hidden="true" />}
        </Button>
      ))}
      <p id={reason} className="max-w-56 text-xs text-muted-foreground">
        {t("unavailable")}
      </p>
    </div>
  );
}

/** Whether a key opens the menu of a cell: Shift+F10, or the Menu key. */
function opensMenu(event: KeyboardEvent<HTMLElement>): boolean {
  return (event.key === "F10" && event.shiftKey) || event.key === "ContextMenu";
}

/** The `contextmenu` events the keyboard sent, which the browser did not. */
const KEYED = new WeakSet<Event>();

/**
 * How long after a key opened the menu a `contextmenu` the browser sends is the echo of that key
 * — the native one of Shift+F10 or of the Menu key, which some browsers send besides —, not a new
 * gesture.
 */
const KEY_ECHO_MS = 1000;

/**
 * Open the menu of the cell that holds the focus from the keyboard, under it, as a right click
 * would: the browser does not open it from Shift+F10 everywhere, nor in a test. Return when it did.
 */
function openFromKeyboard(event: KeyboardEvent<HTMLElement>): boolean {
  const cell = event.target;
  if (!opensMenu(event) || !(cell instanceof HTMLElement) || entering(cell)) {
    return false;
  }
  event.preventDefault();
  const box = cell.getBoundingClientRect();
  const opening = new MouseEvent("contextmenu", {
    bubbles: true,
    cancelable: true,
    clientX: box.left,
    clientY: box.bottom,
  });
  KEYED.add(opening);
  cell.dispatchEvent(opening);
  return true;
}

/**
 * Give the cells of a grid their menu — by a right click, Shift+F10 or the Menu key —, which holds
 * undo and redo, unavailable and saying why: on the body of a grid that offers them, nothing
 * otherwise. The menu adds no stop to the order of tabulation.
 */
export function CellMenu({
  offered,
  disabled,
  children,
}: {
  readonly offered: boolean | undefined;
  /**
   * Whether a cell is being entered: the menu then opens on nothing, and the browser's — paste,
   * spelling — stays the field's, whose entry a menu taking the focus would validate.
   */
  readonly disabled: boolean;
  readonly children: ReactElement;
}) {
  const t = useTranslations("grid.undo");
  const reason = useId();
  // When a key last opened the menu: the native echo of that key moves nothing.
  const keyed = useRef(Number.NEGATIVE_INFINITY);
  if (offered !== true) {
    return children;
  }
  const onKeyDown = (event: KeyboardEvent<HTMLElement>) => {
    if (openFromKeyboard(event)) {
      keyed.current = event.timeStamp;
    }
  };
  const onContextMenu = (event: MouseEvent<HTMLElement>) => {
    if (!KEYED.has(event.nativeEvent) && event.timeStamp - keyed.current < KEY_ECHO_MS) {
      // Prevented, it reaches neither the browser nor the menu, already open.
      event.preventDefault();
    }
  };
  return (
    <ContextMenu>
      <ContextMenuTrigger
        asChild
        disabled={disabled}
        onKeyDown={onKeyDown}
        onContextMenu={onContextMenu}
      >
        {children}
      </ContextMenuTrigger>
      <ContextMenuContent aria-label={t("menu")} className="max-w-64">
        <ContextMenuLabel id={reason} className="text-xs font-normal text-muted-foreground">
          {t("unavailable")}
        </ContextMenuLabel>
        <ContextMenuSeparator />
        {COMMANDS.map((command) => (
          <ContextMenuItem
            key={command}
            aria-disabled
            aria-describedby={reason}
            aria-keyshortcuts={KEYS[command]}
            className={UNAVAILABLE}
            // Pressed, it does nothing, and the menu stays open on the reason.
            onSelect={(event) => {
              event.preventDefault();
            }}
          >
            {command === "undo" ? <Undo2 aria-hidden="true" /> : <Redo2 aria-hidden="true" />}
            {t(command)}
            <kbd className="ml-auto pl-4 font-sans text-xs text-muted-foreground">
              {t(`shortcut.${command}`)}
            </kbd>
          </ContextMenuItem>
        ))}
      </ContextMenuContent>
    </ContextMenu>
  );
}
