// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A command in a menu (US-0580, #1071): the item and its tooltip, from one source. The name is
 * written once, and is both the text of the item and the name its tooltip shows; the keys once, as
 * `aria-keyshortcuts` names them, set on the item, shown at its end and in its tooltip. The item is
 * that of a context menu or of a drop-down menu (`item`), each of shadcn/ui.
 */
"use client";

import type { ComponentType, ReactNode } from "react";

import { CommandTooltip, Keys } from "./command-tooltip";

/** Where an item of a menu shows its keys: at its end, muted. */
const MENU_KEYS_CLASS = "ml-auto pl-4 text-xs text-muted-foreground";

/** What the item of a menu takes of a command: `ContextMenuItem`, `DropdownMenuItem`. */
interface MenuItemProps {
  readonly className?: string;
  readonly onSelect?: (event: Event) => void;
  readonly children: ReactNode;
}

/** What a command of a menu says. */
export interface MenuCommandProps {
  /** The item of the menu it is: `ContextMenuItem` or `DropdownMenuItem`. */
  readonly item: ComponentType<MenuItemProps>;
  /** The name of the command: the text of the item, and the name its tooltip shows. */
  readonly label: string;
  /** What the command does, translated (`CommandTooltip`). */
  readonly help: string;
  /** The keys that press it, as `aria-keyshortcuts` names them; none for a command no key presses. */
  readonly keys?: string | undefined;
  /** The condition it lacks, unavailable (`CommandTooltip`). */
  readonly unavailable?: string | undefined;
  /** What describes it besides its tooltip: the condition said in the menu (`CommandTooltip`). */
  readonly describedBy?: string | undefined;
  /** The icon before its name, drawn already. */
  readonly icon?: ReactNode;
  /** The side its tooltip opens on: right of the item by default. */
  readonly side?: "top" | "right" | "bottom" | "left";
  readonly className?: string;
  /** Pressed: the event of the menu, whose default kept leaves it open. */
  readonly onSelect: (event: Event) => void;
}

/** Render a command in a menu, with its tooltip. */
export function MenuCommand({
  item: Item,
  label,
  help,
  keys,
  unavailable,
  describedBy,
  icon,
  side,
  className,
  onSelect,
}: MenuCommandProps) {
  return (
    <CommandTooltip
      label={label}
      help={help}
      keys={keys}
      unavailable={unavailable}
      describedBy={describedBy}
      inMenu
      {...(side === undefined ? {} : { side })}
    >
      <Item {...(className === undefined ? {} : { className })} onSelect={onSelect}>
        {icon}
        {label}
        <Keys keys={keys} className={MENU_KEYS_CLASS} />
      </Item>
    </CommandTooltip>
  );
}
