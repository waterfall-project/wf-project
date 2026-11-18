// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The template of a screen (charter, guide « Charte graphique »): its `<main>`, in one of the two
 * families of screens (EP-25, « Deux familles d'écrans, dites par Screen ») — a screen of work,
 * dense, the window filled; a screen of settings or of consultation, an airy column centred and
 * bounded —; and its header, the title with the icon of the function and the button of the help of
 * the screen beside it (`HelpPanel`, US-0580), a line under it, and its commands at the right, each
 * with its icon, outlined: the filled button is for the principal command of a card alone
 * (`SectionCard`).
 */
import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

import { cn } from "@/components/ui/utils";

import { HelpPanel } from "./help-panel";

/**
 * The family of a screen, by its density: `dense`, a screen of work — the planning, the estimate,
 * the remaining to commit, the task tree, the actual costs, the Kanban, the timelines, the register
 * of the risks, the audit log —, tight, as wide as the window; `airy`, a screen of settings or of
 * consultation, a column centred in the window and never wider than 96rem (`--container-column`).
 * Each function has its own, in `FUNCTION_DENSITY` and `LEAF_DENSITY`.
 */
export type Density = "dense" | "airy";

/**
 * The classes of the `<main>` of a screen, by density: what its skeleton takes too, at the density
 * its segment passes it. The airy screen takes the margin of the dense one under 1024 points (the
 * breakpoint `lg`), where a zoom of 150 % leaves a grid bar 40 points less than it needs.
 */
export const SCREEN: Readonly<Record<Density, string>> = {
  dense: "flex min-w-0 flex-1 flex-col gap-3 px-5 py-3",
  airy: "mx-auto flex w-full max-w-column min-w-0 flex-1 flex-col gap-7 px-5 py-8 lg:px-10",
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
  density,
  fill = false,
  fillWide = false,
  children,
}: {
  /** Its family: every screen says it, a function by its table (`FUNCTION_DENSITY`). */
  readonly density: Density;
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

/**
 * What the header of a screen shows: its title, its icon, a line under it, its commands; and the
 * button of its help, wherever the table of the functions knows the screen.
 */
export interface PageHeaderProps {
  readonly title: string;
  readonly icon?: LucideIcon | undefined;
  readonly subtitle?: ReactNode;
  /** The commands of the screen, at the right of its title, outlined (`expectCommandRule`). */
  readonly actions?: ReactNode;
  readonly density?: Density;
  /**
   * Whether the header offers the help of the screen at the address; not on a screen that stands
   * in for another — not found, a session refused —, whose address names a screen it does not show.
   */
  readonly helped?: boolean;
}

/** Render the header of a screen. */
export function PageHeader({
  title,
  icon: Icon,
  subtitle,
  actions,
  density = "dense",
  helped = true,
}: PageHeaderProps) {
  return (
    <div className="flex flex-wrap items-start gap-x-4 gap-y-2">
      <div className="flex min-w-[min(100%,24rem)] flex-[0_1_auto] flex-col gap-1">
        {/* The help after the last word of the title, in the flow of its text, an icon alone no
            taller than one of its lines (`1lh`): among the commands it would narrow the whole
            title, and as an item of a row that wraps it would take a line of its own under a
            title on two lines (the remaining to commit on 1280 × 720) — either would make the
            header taller and push the totals of a grid out of a low window. It goes to a line of
            its own only where the last line of the title is full. */}
        <div className={cn("font-semibold", TITLE[density])}>
          <h1 className="inline">
            {Icon === undefined ? null : (
              <Icon
                aria-hidden="true"
                className="mr-2 inline-block size-5 align-middle text-muted-foreground"
              />
            )}
            {title}
          </h1>
          {helped ? (
            // A space, not a margin: at the end of a line it collapses, so that a button the last
            // line of the title has no room for goes to the next line with no indent.
            <>
              {" "}
              <span className="inline-flex h-[1lh] items-center align-top empty:hidden">
                <HelpPanel />
              </span>
            </>
          ) : null}
        </div>
        {subtitle === undefined ? null : (
          <p className="text-sm text-muted-foreground">{subtitle}</p>
        )}
      </div>
      {actions === undefined ? null : (
        <div
          data-slot="screen-commands"
          className="flex min-w-0 flex-1 flex-wrap items-start justify-end gap-2"
        >
          {actions}
        </div>
      )}
    </div>
  );
}
