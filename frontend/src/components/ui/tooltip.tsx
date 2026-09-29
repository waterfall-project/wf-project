// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The tooltip of shadcn/ui, copied into the repository: the name of an entry of the side bar
 * folded into a rail of icons, shown on hover and on the focus of the keyboard. The page in
 * reverse — the foreground token as its surface —, without arrow nor animation: a tooltip
 * repeats a name the control already bears, it never carries one alone.
 */
"use client";

import { Tooltip as TooltipPrimitive } from "radix-ui";
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** Share the delay of the tooltips within it: none, a rail is read at a glance. */
export function TooltipProvider({
  delayDuration = 0,
  ...props
}: ComponentProps<typeof TooltipPrimitive.Provider>) {
  return (
    <TooltipPrimitive.Provider
      data-slot="tooltip-provider"
      delayDuration={delayDuration}
      {...props}
    />
  );
}

/** A tooltip: its trigger and its content. */
export function Tooltip(props: ComponentProps<typeof TooltipPrimitive.Root>) {
  return <TooltipPrimitive.Root data-slot="tooltip" {...props} />;
}

/** The control a tooltip names. */
export function TooltipTrigger(props: ComponentProps<typeof TooltipPrimitive.Trigger>) {
  return <TooltipPrimitive.Trigger data-slot="tooltip-trigger" {...props} />;
}

/** The text of a tooltip, beside its control. */
export function TooltipContent({
  className,
  sideOffset = 4,
  ...props
}: ComponentProps<typeof TooltipPrimitive.Content>) {
  return (
    <TooltipPrimitive.Portal>
      <TooltipPrimitive.Content
        data-slot="tooltip-content"
        sideOffset={sideOffset}
        className={cn(
          "z-50 w-fit rounded-md bg-foreground px-2 py-1 text-xs text-balance text-background",
          className,
        )}
        {...props}
      />
    </TooltipPrimitive.Portal>
  );
}
