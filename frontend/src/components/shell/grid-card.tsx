// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The card of a grid of a screen of work, beside the card of a section (`SectionCard`, EP-25, #3421):
 * the planning, the estimate, the remaining to commit, the task tree, the actual costs, the journal
 * of audit. Bare of any title of section and of any command — the title of the screen says it, and
 * the commands are those of the grid —, it holds what belongs to the grid: its bar, its table, its
 * pages, and above them what only the grid reads, such as the planning start date, so that nothing
 * floats under the title of the screen. A chart that names itself — its caption, its folds and its
 * exports being its own — takes the same form (#3446).
 *
 * The screen stays one of work (`FUNCTION_DENSITY`): tight, as wide as the window; the card fills
 * what the screen leaves it (`Screen fill`) when `fill` is said, its content shrinking to it, the
 * grid down to its floor, never a height computed by hand, and the height of the rows of the grid
 * does not change. `SectionCard` keeps its title required: a card of a section is named, a card of a
 * grid is named by its screen. A server component, which holds no state.
 */
import type { ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/components/ui/utils";

/** Render the card of a grid, which fills what its screen leaves it when `fill` is said. */
export function GridCard({
  fill = false,
  children,
}: {
  /** Whether the screen fills the window (`Screen fill`): the card then takes the room left. */
  readonly fill?: boolean;
  readonly children: ReactNode;
}) {
  return (
    <Card data-slot="grid-card" className={cn("gap-0 py-3", fill ? "min-h-0 flex-1" : null)}>
      <CardContent
        className={cn("flex min-w-0 flex-col gap-2 px-3", fill ? "min-h-0 flex-1" : null)}
      >
        {children}
      </CardContent>
    </Card>
  );
}
