// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The native select of shadcn/ui, copied into the repository: the list a cell of a grid chooses
 * from — a category, a role (WF-IHM-0040). The list of the browser, which the keyboard runs
 * through by its arrows and by the first letters of a name; the border of the `input` token, the
 * ring of the charter under the focus, the chevron of Lucide; no shadow, no transition.
 */
import { ChevronDown } from "lucide-react";
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** Render a list to choose from: the attributes of `<select>`. */
export function NativeSelect({ className, ...props }: ComponentProps<"select">) {
  return (
    <div data-slot="native-select-wrapper" className="relative w-full min-w-0">
      <select
        data-slot="native-select"
        className={cn(
          "h-8 w-full min-w-0 appearance-none rounded-md border border-input bg-background py-1 pr-7 pl-2 text-sm text-foreground outline-none",
          "focus-visible:border-ring focus-visible:ring-[3px] focus-visible:ring-ring aria-invalid:border-destructive",
          className,
        )}
        {...props}
      />
      <ChevronDown
        aria-hidden="true"
        className="pointer-events-none absolute top-1/2 right-2 size-3.5 -translate-y-1/2 text-muted-foreground"
      />
    </div>
  );
}
