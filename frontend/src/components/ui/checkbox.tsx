// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The checkbox of shadcn/ui, copied into the repository: a value held or not, which Radix gives the
 * role of a checkbox and its keyboard — Space checks it. A square with the border of the `input`
 * token, filled with the primary token and marked when checked, the ring of the charter under the
 * focus; no shadow, no transition.
 */
"use client";

import { Check } from "lucide-react";
import { Checkbox as CheckboxPrimitive } from "radix-ui";
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** A value held or not, named by its label. */
export function Checkbox({ className, ...props }: ComponentProps<typeof CheckboxPrimitive.Root>) {
  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      className={cn(
        "size-4 shrink-0 rounded-[4px] border border-input bg-background outline-none focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50 data-[state=checked]:border-primary data-[state=checked]:bg-primary data-[state=checked]:text-primary-foreground",
        className,
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator
        data-slot="checkbox-indicator"
        className="flex items-center justify-center text-current"
      >
        <Check aria-hidden="true" className="size-3.5" />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}
