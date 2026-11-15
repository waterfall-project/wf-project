// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The card of a grid of work of a revision (EP-25, US-2140/L1): the planning, the estimate, the
 * remaining to commit, the task tree and, from US-2140/L2, the actual costs. Bare of any title of
 * section — the title of the screen says it —, it holds what belongs to the grid: its bar, its table, its pages, and above them what only
 * the grid reads, such as the planning start date, so that nothing floats under the title of the
 * screen. The screen stays one of work (`FUNCTION_DENSITY`): tight, as wide as the window; the card
 * fills what the screen leaves it (`Screen fill`), its content shrinking to it, the grid down to
 * its floor, never a height computed by hand, and the height of the rows of the grid does not
 * change. A server component, which holds no state.
 */
import type { ReactNode } from "react";

import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/components/ui/utils";

/** Render the card of a grid of work, which fills what its screen leaves it when `fill` is said. */
export function WorkCard({
  fill = false,
  children,
}: {
  /** Whether the screen fills the window (`Screen fill`): the card then takes the room left. */
  readonly fill?: boolean;
  readonly children: ReactNode;
}) {
  return (
    <Card data-slot="work-card" className={cn("gap-0 py-3", fill ? "min-h-0 flex-1" : null)}>
      <CardContent
        className={cn("flex min-w-0 flex-col gap-2 px-3", fill ? "min-h-0 flex-1" : null)}
      >
        {children}
      </CardContent>
    </Card>
  );
}
