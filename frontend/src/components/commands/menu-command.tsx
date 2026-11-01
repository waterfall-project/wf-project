// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A command in a menu (US-0580, #1071): the item and its tooltip, from one source. The name is
 * written once, and is both the text of the item and the name its tooltip shows; the keys once, as
 * `aria-keyshortcuts` names them, set on the item, shown at its end and in its tooltip. The item is
 * that of a context menu or of a drop-down menu (`item`), each of shadcn/ui; a command that leads
 * elsewhere is a link the item renders (`href`), and one that says under its name the condition it
 * lacks carries it (`detail`, US-0670/L5, #1435).
 */
"use client";

import Link from "next/link";
import type { ComponentType, ReactNode } from "react";

import { CommandTooltip, Keys } from "./command-tooltip";

/** Where an item of a menu shows its keys: at its end, muted. */
const MENU_KEYS_CLASS = "ml-auto pl-4 text-xs text-muted-foreground";

/** What the item of a menu takes of a command: `ContextMenuItem`, `DropdownMenuItem`. */
interface MenuItemProps {
  readonly asChild?: boolean;
  readonly className?: string;
  readonly onSelect?: (event: Event) => void;
  readonly children: ReactNode;
}

/** What a command of a menu does: a gesture pressed, or a link followed. */
type MenuCommandAction =
  | {
      /** Pressed: the event of the menu, whose default kept leaves it open. */
      readonly onSelect: (event: Event) => void;
      readonly href?: never;
    }
  | {
      /** The address the command leads to, a link the item renders. */
      readonly href: string;
      readonly onSelect?: never;
    };

/** What a command of a menu says. */
export type MenuCommandProps = MenuCommandAction & {
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
  /** What the item says under its name — the condition it lacks, said in the menu. */
  readonly detail?: ReactNode;
  /** The side its tooltip opens on: right of the item by default. */
  readonly side?: "top" | "right" | "bottom" | "left";
  readonly className?: string;
};

/** Render a command in a menu, with its tooltip. */
export function MenuCommand({
  item: Item,
  label,
  help,
  keys,
  unavailable,
  describedBy,
  icon,
  detail,
  side,
  className,
  onSelect,
  href,
}: MenuCommandProps) {
  const content = (
    <>
      {icon}
      {detail === undefined ? (
        label
      ) : (
        <span>
          {label}
          {detail}
        </span>
      )}
      <Keys keys={keys} className={MENU_KEYS_CLASS} />
    </>
  );
  const styled = className === undefined ? {} : { className };
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
      {href === undefined ? (
        <Item {...styled} onSelect={onSelect}>
          {content}
        </Item>
      ) : (
        <Item {...styled} asChild>
          <Link href={href}>{content}</Link>
        </Item>
      )}
    </CommandTooltip>
  );
}
