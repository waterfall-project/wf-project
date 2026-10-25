// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The tooltip of shadcn/ui, copied into the repository: the name of an entry of the side bar
 * folded into a rail of icons, and the tooltip of every command (`CommandTooltip`), shown on hover
 * and on the focus of the keyboard. The page in reverse — the foreground token as its surface —,
 * without arrow nor animation: a tooltip repeats a name the control already bears, it never
 * carries one alone.
 *
 * The tooltips of the application share one provider, at the root of the shell: one tooltip
 * closed, the next one the pointer reaches opens at once, its delay skipped, as a bar is read from
 * one command to the next. Each tooltip says its own delay (`delayDuration` of `Tooltip`). A
 * tooltip rendered outside any provider — a component rendered alone, in its test — brings its own,
 * which shares nothing.
 */
"use client";

import { Tooltip as TooltipPrimitive } from "radix-ui";
import { type ComponentProps, createContext, use } from "react";

import { cn } from "./utils";

/** Whether a provider is above: the tooltips under it share it. */
const Provided = createContext(false);

/** Share the delays of the tooltips within it: none by default, a rail is read at a glance. */
export function TooltipProvider({
  delayDuration = 0,
  ...props
}: ComponentProps<typeof TooltipPrimitive.Provider>) {
  return (
    <Provided value>
      <TooltipPrimitive.Provider
        data-slot="tooltip-provider"
        delayDuration={delayDuration}
        {...props}
      />
    </Provided>
  );
}

/** A tooltip: its trigger and its content; under the provider above, or its own. */
export function Tooltip(props: ComponentProps<typeof TooltipPrimitive.Root>) {
  const root = <TooltipPrimitive.Root data-slot="tooltip" {...props} />;
  return use(Provided) ? root : <TooltipProvider>{root}</TooltipProvider>;
}

/** The control a tooltip names. */
export function TooltipTrigger(props: ComponentProps<typeof TooltipPrimitive.Trigger>) {
  return <TooltipPrimitive.Trigger data-slot="tooltip-trigger" {...props} />;
}

/**
 * The text of a tooltip, beside its control. It takes the pointer even where a modal menu leaves
 * the body none (`pointer-events: none`): the pointer passes over it, and it stays open
 * (WCAG 1.4.13).
 */
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
          "pointer-events-auto z-50 w-fit rounded-md bg-foreground px-2 py-1 text-xs text-balance text-background",
          className,
        )}
        {...props}
      />
    </TooltipPrimitive.Portal>
  );
}
