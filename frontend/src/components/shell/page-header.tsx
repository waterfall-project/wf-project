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

const SCREEN: Readonly<Record<Density, string>> = {
  dense: "flex min-w-0 flex-1 flex-col gap-3 px-5 py-3",
  airy: "flex min-w-0 flex-1 flex-col gap-7 px-10 py-8",
};

const TITLE: Readonly<Record<Density, string>> = {
  dense: "text-lg",
  airy: "text-2xl",
};

/** The main content of a screen, at its density. */
export function Screen({
  density = "dense",
  children,
}: {
  readonly density?: Density;
  readonly children: ReactNode;
}) {
  return <main className={SCREEN[density]}>{children}</main>;
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
