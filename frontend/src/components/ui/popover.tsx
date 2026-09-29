// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The popover of shadcn/ui, copied into the repository: why a cell of a grid is not entered, told
 * beside it (WF-IHM-0030). Radix gives it the role of a dialog, takes the focus into it as it
 * opens, closes it on Escape or on a click outside, and gives the focus back to its trigger. The
 * surface of the popover token, a border and the one shadow of the charter, which sets a layer
 * over the page apart from it; no animation.
 */
"use client";

import { Popover as PopoverPrimitive } from "radix-ui";
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** A popover: its trigger and its content. */
export function Popover(props: ComponentProps<typeof PopoverPrimitive.Root>) {
  return <PopoverPrimitive.Root data-slot="popover" {...props} />;
}

/** The control that opens a popover. */
export function PopoverTrigger(props: ComponentProps<typeof PopoverPrimitive.Trigger>) {
  return <PopoverPrimitive.Trigger data-slot="popover-trigger" {...props} />;
}

/** What a popover says, over the page, beside its trigger. */
export function PopoverContent({
  className,
  align = "center",
  sideOffset = 4,
  ...props
}: ComponentProps<typeof PopoverPrimitive.Content>) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        data-slot="popover-content"
        align={align}
        sideOffset={sideOffset}
        className={cn(
          "z-50 w-72 rounded-md border bg-popover p-3 text-popover-foreground shadow-md outline-hidden",
          className,
        )}
        {...props}
      />
    </PopoverPrimitive.Portal>
  );
}
