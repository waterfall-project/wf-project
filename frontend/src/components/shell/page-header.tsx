// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The template of a screen (charter, guide « Charte graphique »): its `<main>`, dense for the
 * grids and the lists — the most information under the eyes — or airy for the indicators; and
 * its header, the title with the icon of the function, a line under it, and its commands at the
 * right, each with its icon.
 */
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/components/ui/utils";

/** How much a screen holds: dense for a grid or a list, airy for indicators. */
export type Density = "dense" | "airy";

/** The classes of the `<main>` of a screen, by density: what its skeleton takes too. */
export const SCREEN: Readonly<Record<Density, string>> = {
  dense: "flex min-w-0 flex-1 flex-col gap-3 px-5 py-3",
  airy: "flex min-w-0 flex-1 flex-col gap-7 px-10 py-8",
};

const TITLE: Readonly<Record<Density, string>> = {
  dense: "text-lg",
  airy: "text-2xl",
};

/**
 * The main content of a screen, at its density. A screen that fills the window — a grid —
 * bounds the page to its height (`ShellFrame`) and shrinks to what is left under the bar and
 * the banner, so that the element that scrolls in it, the grid, keeps its edges in view: the
 * layout gives it its height, never a height computed by hand from what lies above it. When
 * the window is too low for its content at its least, the content overflows it and the page
 * scrolls.
 */
export function Screen({
  density = "dense",
  fill = false,
  fillWide = false,
  children,
}: {
  readonly density?: Density;
  readonly fill?: boolean;
  /**
   * Whether the screen fills the window from the large breakpoint only: a screen that sets its
   * grid beside other content there, and stacks them in a narrow window, where the page scrolls.
   */
  readonly fillWide?: boolean;
  readonly children: ReactNode;
}) {
  return (
    <main
      data-fill={fill ? "" : undefined}
      data-fill-lg={fillWide ? "" : undefined}
      className={cn(SCREEN[density], fill ? "min-h-0" : null, fillWide ? "lg:min-h-0" : null)}
    >
      {children}
    </main>
  );
}

/** What the header of a screen shows: its title, its icon, a line under it, its commands. */
export interface PageHeaderProps {
  readonly title: string;
  readonly icon?: LucideIcon | undefined;
  readonly subtitle?: ReactNode;
  /** The commands of the screen, at the right of its title. */
  readonly actions?: ReactNode;
  readonly density?: Density;
}

/** Render the header of a screen. */
export function PageHeader({
  title,
  icon: Icon,
  subtitle,
  actions,
  density = "dense",
}: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
      <div className="flex min-w-0 flex-1 flex-col gap-1">
        <h1 className={cn("flex items-center gap-2 font-semibold", TITLE[density])}>
          {Icon === undefined ? null : (
            <Icon aria-hidden="true" className="size-5 shrink-0 text-muted-foreground" />
          )}
          {title}
        </h1>
        {subtitle === undefined ? null : (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
      {actions === undefined ? null : (
        <div className="flex flex-wrap items-start gap-2">{actions}</div>
      )}
    </div>
  );
}
