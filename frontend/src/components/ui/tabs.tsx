// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A row of tabs: the choice of a current one among a few — a chronology, a depth of a tree, a
 * perimeter. The fill is kept for the main command of a card; a current choice is said otherwise
 * (US-2070, #3088, #3090): the current tab is underlined in the primary and written in the text of
 * the page, the others muted and without a line.
 *
 * Each choice is a link, or a button that toggles, which takes `tabVariants` itself — as a link
 * that looks like a button takes `buttonVariants`: the current one is said by `aria-current` (a
 * link) or `aria-pressed` (a button), so that a reader of the screen hears it and the look follows
 * it. The row is a `nav` named by its choice, not a `tablist`: its choices lead to an address or
 * filter the screen, they do not switch panels under it.
 */
import { cva } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** The classes of a tab: muted, and underlined in the primary when it is the current one. */
export const tabVariants = cva(
  "-mb-px inline-flex h-8 shrink-0 items-center gap-2 border-b-2 border-transparent px-3 text-sm font-medium whitespace-nowrap text-muted-foreground outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring aria-pressed:border-primary aria-pressed:text-foreground aria-[current=page]:border-primary aria-[current=page]:text-foreground aria-[current=true]:border-primary aria-[current=true]:text-foreground [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
);

/** Render a row of tabs, named by the choice it offers (`aria-label`). */
export function Tabs({
  className,
  ...props
}: ComponentProps<"nav"> & { readonly "aria-label": string }) {
  return (
    <nav
      data-slot="tabs"
      className={cn("flex flex-wrap items-end gap-1 border-b border-border", className)}
      {...props}
    />
  );
}
