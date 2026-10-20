// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The key figures of a screen, in cards (US-0550): a card is a region named by its title, which
 * carries the date its figures are computed at when the answer has one (WF-IHM-0020) and the
 * figures themselves, in a list of terms (`FiguresList`, a `dl`) that keeps its meaning for a
 * screen reader — a name, then its value. The cards of a screen lie in `FiguresGrid`, which wraps
 * to the next line as the width asks. Nothing here computes or formats a figure (WF-ARC-0020):
 * the caller writes what the API gave.
 */
import type { ReactNode } from "react";

import { CalculationDate, type CalculationContext } from "@/components/context/indicator";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/components/ui/utils";

/** The cards of a screen, side by side as far as the width allows, then on the next line. */
export function FiguresGrid({
  children,
  className,
}: {
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <div
      className={cn(
        "grid grid-cols-[repeat(auto-fit,minmax(min(100%,12rem),1fr))] items-start gap-4",
        className,
      )}
    >
      {children}
    </div>
  );
}

/** A card of figures: its title, the date they are computed at when there is one, its content. */
export function FiguresCard({
  title,
  context,
  children,
  className,
  inline = false,
}: {
  readonly title: string;
  /** The calculation context of the answer, when it has one. */
  readonly context?: CalculationContext;
  /** The title beside the figures rather than above them, for a card of one row. */
  readonly inline?: boolean;
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <Card
      role="region"
      aria-label={title}
      className={cn("gap-2 py-3", inline && "flex-row flex-wrap items-center gap-x-6", className)}
    >
      <CardHeader className="flex flex-wrap items-baseline gap-x-3 gap-y-0 px-4">
        <CardTitle className="text-sm">{title}</CardTitle>
        {context === undefined ? null : (
          <CardDescription>
            <CalculationDate context={context} />
          </CardDescription>
        )}
      </CardHeader>
      <CardContent className={cn("space-y-2 px-4 text-sm", inline && "min-w-0 grow")}>
        {children}
      </CardContent>
    </Card>
  );
}

/**
 * The figures of a card, a name and its value each: a list of terms, one entry to a row, in as
 * many columns as the card is wide.
 */
export function FiguresList({
  children,
  className,
}: {
  readonly children: ReactNode;
  readonly className?: string;
}) {
  return (
    <dl
      className={cn(
        "grid grid-cols-[repeat(auto-fill,minmax(min(100%,11rem),1fr))] gap-x-6 gap-y-1",
        className,
      )}
    >
      {children}
    </dl>
  );
}

/** An entry of `FiguresList`: its name, then its value, on the one row while they fit. */
export function FigureTerm({
  name,
  children,
}: {
  readonly name: string;
  readonly children: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-baseline justify-between gap-x-3">
      <dt className="text-xs text-muted-foreground">{name}</dt>
      <dd className="font-semibold tabular-nums">{children}</dd>
    </div>
  );
}
