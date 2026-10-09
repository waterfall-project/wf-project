// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The field of shadcn/ui, copied into the repository: the border of the `input` token, which
 * shows where to type at 3:1, the ring of the charter under the focus, and no shadow.
 */
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** Render a field of the charter: the attributes of `<input>`. */
export function Input({ className, type, ...props }: ComponentProps<"input">) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        "h-8 w-full min-w-0 rounded-md border border-input bg-background px-3 py-1 text-sm text-foreground outline-none placeholder:text-muted-foreground disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring",
        className,
      )}
      {...props}
    />
  );
}
