// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The context menu of shadcn/ui, copied into the repository, the parts a grid uses: the menu of a
 * cell, opened by a right click or, from the keyboard, by Shift+F10 or the Menu key. Radix gives it
 * the roles of a menu and its keyboard — the arrows, Enter, Escape — and gives the focus back to
 * what held it once closed; a submenu, with its checked entries or its choice among values, is the
 * one a command offers several values with. The surface of the popover token, a border and the one
 * shadow of the charter, as the drop-down menu; no animation.
 */
"use client";

import { Check, ChevronRight } from "lucide-react";
import { ContextMenu as ContextMenuPrimitive } from "radix-ui";
import type { ComponentProps } from "react";

import { cn } from "./utils";

const SURFACE =
  "z-50 min-w-[8rem] overflow-x-hidden overflow-y-auto rounded-md border bg-popover p-1 text-popover-foreground shadow-md";
const ENTRY =
  "relative flex cursor-default items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-hidden select-none focus:bg-accent focus:text-accent-foreground data-[disabled]:pointer-events-none data-[disabled]:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4 [&_svg:not([class*='text-'])]:text-muted-foreground";

/** A context menu: the area it opens on, and its content. */
export function ContextMenu(props: ComponentProps<typeof ContextMenuPrimitive.Root>) {
  return <ContextMenuPrimitive.Root data-slot="context-menu" {...props} />;
}

/** The area a right click opens the menu on. */
export function ContextMenuTrigger(props: ComponentProps<typeof ContextMenuPrimitive.Trigger>) {
  return <ContextMenuPrimitive.Trigger data-slot="context-menu-trigger" {...props} />;
}

/** The entries of a context menu, over the page, where it was opened. */
export function ContextMenuContent({
  className,
  ...props
}: ComponentProps<typeof ContextMenuPrimitive.Content>) {
  return (
    <ContextMenuPrimitive.Portal>
      <ContextMenuPrimitive.Content
        data-slot="context-menu-content"
        className={cn(SURFACE, "max-h-(--radix-context-menu-content-available-height)", className)}
        {...props}
      />
    </ContextMenuPrimitive.Portal>
  );
}

/** An entry of a context menu. */
export function ContextMenuItem({
  className,
  ...props
}: ComponentProps<typeof ContextMenuPrimitive.Item>) {
  return (
    <ContextMenuPrimitive.Item
      data-slot="context-menu-item"
      className={cn(ENTRY, className)}
      {...props}
    />
  );
}

/** A label within a context menu: what the entries after it are about. */
export function ContextMenuLabel({
  className,
  ...props
}: ComponentProps<typeof ContextMenuPrimitive.Label>) {
  return (
    <ContextMenuPrimitive.Label
      data-slot="context-menu-label"
      className={cn("px-2 py-1.5 text-sm font-medium", className)}
      {...props}
    />
  );
}

/** A line between two groups of entries. */
export function ContextMenuSeparator({
  className,
  ...props
}: ComponentProps<typeof ContextMenuPrimitive.Separator>) {
  return (
    <ContextMenuPrimitive.Separator
      data-slot="context-menu-separator"
      className={cn("-mx-1 my-1 h-px bg-border", className)}
      {...props}
    />
  );
}

/** A submenu: its entry in the menu, and what it opens. */
export function ContextMenuSub(props: ComponentProps<typeof ContextMenuPrimitive.Sub>) {
  return <ContextMenuPrimitive.Sub {...props} />;
}

/** The entry of a menu that opens a submenu, marked by a chevron. */
export function ContextMenuSubTrigger({
  className,
  children,
  ...props
}: ComponentProps<typeof ContextMenuPrimitive.SubTrigger>) {
  return (
    <ContextMenuPrimitive.SubTrigger
      data-slot="context-menu-sub-trigger"
      className={cn(ENTRY, "data-[state=open]:bg-accent", className)}
      {...props}
    >
      {children}
      <ChevronRight aria-hidden="true" className="ml-auto" />
    </ContextMenuPrimitive.SubTrigger>
  );
}

/** The entries of a submenu, beside the entry that opened it. */
export function ContextMenuSubContent({
  className,
  ...props
}: ComponentProps<typeof ContextMenuPrimitive.SubContent>) {
  return (
    <ContextMenuPrimitive.Portal>
      <ContextMenuPrimitive.SubContent
        data-slot="context-menu-sub-content"
        className={cn(SURFACE, className)}
        {...props}
      />
    </ContextMenuPrimitive.Portal>
  );
}

/** An entry that is on or off, a mark in front when on. */
export function ContextMenuCheckboxItem({
  className,
  children,
  ...props
}: ComponentProps<typeof ContextMenuPrimitive.CheckboxItem>) {
  return (
    <ContextMenuPrimitive.CheckboxItem
      data-slot="context-menu-checkbox-item"
      className={cn(ENTRY, "pl-8", className)}
      {...props}
    >
      <span className="pointer-events-none absolute left-2 flex size-4 items-center justify-center">
        <ContextMenuPrimitive.ItemIndicator>
          <Check aria-hidden="true" className="size-4 text-foreground" />
        </ContextMenuPrimitive.ItemIndicator>
      </span>
      {children}
    </ContextMenuPrimitive.CheckboxItem>
  );
}

/** A choice among values, one of which is checked. */
export function ContextMenuRadioGroup(
  props: ComponentProps<typeof ContextMenuPrimitive.RadioGroup>,
) {
  return <ContextMenuPrimitive.RadioGroup data-slot="context-menu-radio-group" {...props} />;
}

/** One value of a choice, checked or not: a mark in front of the one checked. */
export function ContextMenuRadioItem({
  className,
  children,
  ...props
}: ComponentProps<typeof ContextMenuPrimitive.RadioItem>) {
  return (
    <ContextMenuPrimitive.RadioItem
      data-slot="context-menu-radio-item"
      className={cn(ENTRY, "pl-8", className)}
      {...props}
    >
      <span className="pointer-events-none absolute left-2 flex size-4 items-center justify-center">
        <ContextMenuPrimitive.ItemIndicator>
          <Check aria-hidden="true" className="size-4 text-foreground" />
        </ContextMenuPrimitive.ItemIndicator>
      </span>
      {children}
    </ContextMenuPrimitive.RadioItem>
  );
}
