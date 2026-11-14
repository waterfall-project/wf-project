// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The button of shadcn/ui, copied into the repository and held to its rules: its colours are
 * the tokens of the charter, and it casts no shadow. Without `asChild`: a link that looks like
 * a button takes `buttonVariants` on the link itself.
 *
 * The charter of EP-25 (US-2070, #3079): a pill. A button that cannot be pressed now looks the
 * same whether it is `disabled` or marked `aria-disabled` (#3125) — the latter keeps the pointer,
 * for the tooltip that says what it lacks and the press that says it again. The commands of a row
 * of a table (`row`) keep a border, the light one of the tables, and a label of normal weight.
 */
import { cva, type VariantProps } from "class-variance-authority";
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** The classes of a button, by variant and size. */
export const buttonVariants = cva(
  "inline-flex shrink-0 items-center justify-center gap-2 rounded-full text-sm whitespace-nowrap outline-none focus-visible:ring-[3px] focus-visible:ring-ring disabled:pointer-events-none disabled:opacity-50 aria-disabled:cursor-not-allowed aria-disabled:opacity-50 [&_svg]:pointer-events-none [&_svg]:shrink-0 [&_svg:not([class*='size-'])]:size-4",
  {
    variants: {
      // The weight is the variant's, never the base's: a link takes these classes without the
      // merge of `cn`, and two weights in one list would leave the stylesheet to choose.
      variant: {
        default: "bg-primary font-medium text-primary-foreground hover:bg-primary-hover",
        outline:
          "border border-input bg-background font-medium hover:bg-accent hover:text-accent-foreground",
        ghost: "font-medium hover:bg-accent hover:text-accent-foreground",
        row: "border border-border bg-transparent font-normal hover:bg-accent hover:text-accent-foreground",
      },
      size: {
        default: "h-9 px-4 py-2",
        sm: "h-8 px-3",
        icon: "size-8",
      },
    },
    defaultVariants: { variant: "default", size: "default" },
  },
);

/** A button: the attributes of `<button>`, and a variant and a size of the charter. */
export type ButtonProps = ComponentProps<"button"> & VariantProps<typeof buttonVariants>;

/** Render a button of the charter. */
export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size, className }))} {...props} />;
}
