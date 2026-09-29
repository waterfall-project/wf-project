// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The alert of shadcn/ui, copied into the repository as far as the screens of the way in and of
 * the account need it: a notice in the page, its icon at the left, its title and its
 * description. What it announces is its user's to say — `role="status"` for what was done,
 * `role="alert"` for what went wrong —: it carries no role of its own. The surface of the card,
 * a border; the destructive variant writes in the destructive token.
 */
import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "./utils";

const alertVariants = cva(
  "grid w-full grid-cols-[1rem_1fr] items-start gap-x-3 gap-y-0.5 rounded-lg border bg-card px-4 py-3 text-sm [&>svg]:size-4 [&>svg]:translate-y-0.5 [&>svg]:text-current",
  {
    variants: {
      variant: {
        default: "text-card-foreground",
        destructive: "text-destructive",
      },
    },
    defaultVariants: { variant: "default" },
  },
);

/** A notice in the page, in a variant of the charter. */
export function Alert({
  className,
  variant,
  ...props
}: ComponentProps<"div"> & VariantProps<typeof alertVariants>) {
  return <div data-slot="alert" className={cn(alertVariants({ variant }), className)} {...props} />;
}

/** The title of a notice, beside its icon. */
export function AlertTitle({ className, ...props }: ComponentProps<"p">) {
  return (
    <p
      data-slot="alert-title"
      className={cn("col-start-2 font-medium tracking-tight", className)}
      {...props}
    />
  );
}

/** What a notice says, under its title. */
export function AlertDescription({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-description"
      className={cn("col-start-2 grid justify-items-start gap-1 text-sm", className)}
      {...props}
    />
  );
}
