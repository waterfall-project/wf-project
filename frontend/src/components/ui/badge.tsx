// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The badge of shadcn/ui, copied into the repository: a short state beside what it qualifies —
 * the status of a revision, a count —, in the tokens of the charter. A badge says its state in
 * words: it never tells two states apart by its colour alone.
 */
import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** The classes of a badge, by variant. */
export const badgeVariants = cva(
  "inline-flex w-fit shrink-0 items-center justify-center gap-1 overflow-hidden rounded-md border px-1.5 py-px text-xs font-medium whitespace-nowrap [&>svg]:pointer-events-none [&>svg]:size-3",
  {
    variants: {
      variant: {
        secondary: "border-border bg-secondary text-secondary-foreground",
        outline: "border-border bg-background text-foreground",
      },
    },
    defaultVariants: { variant: "secondary" },
  },
);

/** A badge: the attributes of `<span>`, and a variant of the charter. */
export type BadgeProps = ComponentProps<"span"> & VariantProps<typeof badgeVariants>;

/** Render a badge of the charter. */
export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span data-slot="badge" className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
