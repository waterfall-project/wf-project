// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Undo and redo of the entries of a revision (WF-IHM-0110), placed where they will act — in the
 * bar of a grid that enters a revision in progress, in its menu of edition, and by Ctrl+Z and
 * Ctrl+Shift+Z on the grid — but not wired: the server keeps no history of the entries yet, and
 * EP-06 wires them on `undoLastChange` and `redoLastUndo`, the undoing being the server's, never a
 * stack in the browser (WF-ARC-0070). Until then they are unavailable, and say why: the buttons and
 * the entries of the menu stay in the order of the keyboard, marked `aria-disabled` and described
 * by the reason, and the shortcut tells it in a region announced.
 *
 * Only a grid that enters a revision in progress offers them: none undoes a marking, an import
 * applied or the exclusion of a line of actual cost, which no such grid makes.
 *
 * The shortcut is the grid's alone, and never a field's being entered: Ctrl+Z in the editor of a
 * cell, or in the search, stays the browser's, which undoes what was typed in it.
 */
"use client";

import { PenLine, Redo2, Undo2 } from "lucide-react";
import { useTranslations } from "next-intl";
import { type KeyboardEvent, useId, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/components/ui/utils";

/** The two commands. */
export type UndoCommand = "undo" | "redo";

const COMMANDS: readonly UndoCommand[] = ["undo", "redo"];

/** The shortcut of each command, as `aria-keyshortcuts` names it. */
const KEYS: Readonly<Record<UndoCommand, string>> = {
  undo: "Control+Z",
  redo: "Control+Shift+Z",
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

/** Render the region that tells the shortcut pressed unavailable, present before it is. */
export function UndoAnnouncer({ told }: { readonly told: UndoShortcut["told"] }) {
  const t = useTranslations("grid.undo");
  return (
    <div role="status" aria-live="polite" className="sr-only">
      {/* A new node each time, so that the same command pressed again is heard again. */}
      {told === undefined ? null : <p key={told.count}>{t(`told.${told.command}`)}</p>}
    </div>
  );
}

/** Render the commands in the bar of a grid: their buttons, their menu, and why they wait. */
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
      <UndoMenu />
    </div>
  );
}

/** Render the menu of edition, its entries unavailable and saying why. */
function UndoMenu() {
  const t = useTranslations("grid.undo");
  const reason = useId();
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="outline" size="sm" className="h-7 text-xs">
          <PenLine aria-hidden="true" />
          {t("menu")}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="max-w-64">
        <DropdownMenuLabel id={reason} className="text-xs font-normal text-muted-foreground">
          {t("unavailable")}
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {COMMANDS.map((command) => (
          <DropdownMenuItem
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
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
