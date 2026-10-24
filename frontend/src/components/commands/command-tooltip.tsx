// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The tooltip of a command (US-0580, #1071): beside a button, a link or an item of a menu, its name,
 * a sentence that says what it does — the help the catalogue holds for the command,
 * `commands.<command>.help` —, the keys that press it, and, the command unavailable, the condition it
 * lacks (WF-IHM-0090). Every button of the application bears one; none bears a `title`, which the
 * browser shows late, unstyled, and never on the focus of the keyboard.
 *
 * The keys are written once, as `aria-keyshortcuts` names them (`shortcut.ts`): the tooltip sets the
 * attribute on the control and shows the same keys in `<kbd>`, the way of the workstation — Cmd on a
 * Mac, Ctrl elsewhere —, so that the two never part. A command unavailable is marked `aria-disabled`,
 * never `disabled`, which would take it out of the reach of the pointer and of the keyboard: it is
 * hovered and focused, and its tooltip says why it waits.
 *
 * WCAG 1.4.13: the tooltip opens on hover as on the focus of the keyboard, closes by Escape, the
 * focus left where it is, and stays open while the pointer passes over it; it describes its control
 * (`aria-describedby`, by the help alone: the name is the control's, and the condition the text that
 * says it beside the command, which the control is described by too). It never carries alone what
 * the user needs: the name stays the control's accessible name, the condition its description, as
 * the screen said them before the tooltip came.
 */
"use client";

import { useTranslations } from "next-intl";
import { type ReactElement, useEffect, useRef, useState, useSyncExternalStore } from "react";

import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "@/components/ui/tooltip";
import type { Catalogue } from "@/i18n/catalogues";

import { isModifier, isNamedKey, onMac, type Platform, shownWays } from "./shortcut";

/** The commands the catalogue holds a help for: each key of `commands` with a `help`. */
export type CommandHelp = {
  [K in keyof Catalogue["commands"]]: Catalogue["commands"][K] extends { readonly help: string }
    ? K
    : never;
}[keyof Catalogue["commands"]];

/**
 * How long the pointer rests on a command before its tooltip opens: long enough for a bar crossed on
 * the way elsewhere to open none. The focus of the keyboard opens it at once.
 */
const HOVER_DELAY_MS = 300;

/** Where an item of a menu shows its keys: at its end, muted. */
export const MENU_KEYS_CLASS = "ml-auto pl-4 text-xs text-muted-foreground";

/** A store that never changes: the workstation stays what it is. */
function unchanging(): () => void {
  return () => undefined;
}

/** The workstation in the browser. */
function platformNow(): Platform {
  return onMac() ? "mac" : "other";
}

/** The server knows no workstation: any other than a Mac, until the page is hydrated. */
function noPlatform(): Platform {
  return "other";
}

/** The workstation the keys are written for, read once the page is hydrated. */
export function usePlatform(): Platform {
  return useSyncExternalStore(unchanging, platformNow, noPlatform);
}

/**
 * The keys of a command, as the workstation writes them, each way of pressing it in a `<kbd>`:
 * hidden from a screen reader, which reads them from `aria-keyshortcuts`, where the same keys are
 * written. Nothing for no keys.
 */
export function Keys({
  keys,
  className,
}: {
  /** The keys, as `aria-keyshortcuts` names them. */
  readonly keys: string | undefined;
  readonly className?: string;
}) {
  const t = useTranslations("commands");
  const platform = usePlatform();
  const ways = shownWays(keys, platform);
  if (ways.length === 0) {
    return null;
  }
  const named = (key: string) => {
    if (platform === "mac" && isModifier(key) && isNamedKey(key)) {
      return t(`macKeys.${key as "Control" | "Meta" | "Alt" | "Shift"}`);
    }
    return isNamedKey(key) ? t(`keys.${key}`) : key;
  };
  return (
    <span aria-hidden="true" className={className}>
      {ways.map((way, at) => (
        <span key={way.join("+")}>
          {at === 0 ? null : t("or")}
          <kbd className="font-sans">{way.map(named).join(platform === "mac" ? "" : "+")}</kbd>
        </span>
      ))}
    </span>
  );
}

/** What a tooltip says of its command. */
export interface CommandTooltipProps {
  /** The name of the command, as its control bears it: the tooltip opens on it. */
  readonly label: string;
  /** The command whose help the catalogue holds (`commands.<help>.help`). */
  readonly help: CommandHelp;
  /**
   * The keys that press the command, as `aria-keyshortcuts` names them: set on the control, and
   * shown in the tooltip. None for a command no key presses.
   */
  readonly keys?: string | undefined;
  /**
   * The condition the command lacks, the command unavailable: said in the tooltip, and the control
   * marked `aria-disabled`; none for a command available.
   */
  readonly unavailable?: string | undefined;
  /**
   * The identifiers of what describes the control besides the tooltip — the condition said beside
   * the command —: the tooltip open describes it too.
   */
  readonly describedBy?: string | undefined;
  /** The side of the control the tooltip opens on: below it, or beside an item of a menu. */
  readonly side?: "top" | "right" | "bottom" | "left";
  /**
   * Whether the control is an item of a menu, whose tooltip opens beside it once the pointer or the
   * focus rests on the item — the keyboard going through a menu item by item —, so that Escape
   * pressed at once closes the menu; open, Escape closes the tooltip first, as everywhere.
   */
  readonly inMenu?: boolean;
  /**
   * The control: a button, a link, an item of a menu — one element, which takes the attributes and
   * the events of the tooltip, and sets no `aria-describedby` of its own (`describedBy`).
   */
  readonly children: ReactElement;
}

/** Give a command its tooltip. */
export function CommandTooltip({
  label,
  help,
  keys,
  unavailable,
  describedBy,
  inMenu = false,
  side = inMenu ? "right" : "bottom",
  children,
}: CommandTooltipProps) {
  const t = useTranslations("commands");
  const sentence = t(`${help}.help`);
  const [open, setOpen] = useState(false);
  const resting = useRef<number | undefined>(undefined);
  useEffect(
    () => () => {
      window.clearTimeout(resting.current);
    },
    [],
  );
  // A rest given up: the control pressed, left or blurred. Radix tells no closing of a tooltip it
  // holds closed already, and the rest under way would open it after the press.
  const giveUp = () => {
    window.clearTimeout(resting.current);
  };
  const openWhen = (opened: boolean) => {
    giveUp();
    if (opened && inMenu) {
      resting.current = window.setTimeout(() => {
        setOpen(true);
      }, HOVER_DELAY_MS);
    } else {
      setOpen(opened);
    }
  };
  return (
    // In a menu, the rest is timed here, for the focus as for the pointer.
    <TooltipProvider delayDuration={inMenu ? 0 : HOVER_DELAY_MS}>
      <Tooltip open={open} onOpenChange={openWhen}>
        <TooltipTrigger
          asChild
          aria-keyshortcuts={keys}
          aria-disabled={unavailable === undefined ? undefined : true}
          aria-describedby={describedBy}
          onPointerDown={giveUp}
          onPointerLeave={giveUp}
          onKeyDown={giveUp}
          onBlur={giveUp}
        >
          {children}
        </TooltipTrigger>
        <TooltipContent
          side={side}
          // What the control is described by: the help, the name being its own and the condition
          // said where the command is.
          aria-label={sentence}
          className="max-w-72 space-y-1 text-left text-pretty"
        >
          <p className="font-medium">{label}</p>
          <p>{sentence}</p>
          {unavailable === undefined ? null : <p>{unavailable}</p>}
          <Keys keys={keys} className="block opacity-80" />
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}
