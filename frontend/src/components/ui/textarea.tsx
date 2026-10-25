// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The multi-line field of shadcn/ui, copied into the repository: the border of the `input` token,
 * the ring of the charter under the focus, and no shadow — the field of `input.tsx`, taller.
 */
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** Render a multi-line field of the charter: the attributes of `<textarea>`. */
export function Textarea({ className, ...props }: ComponentProps<"textarea">) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        "min-h-16 w-full min-w-0 rounded-md border border-input bg-background px-3 py-1.5 text-sm text-foreground outline-none placeholder:text-muted-foreground disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
        "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring aria-invalid:border-destructive",
        className,
      )}
      {...props}
    />
  );
}
