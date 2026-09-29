// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The table of shadcn/ui, copied into the repository for the dense grid: its container is the
 * element that scrolls, on both axes, so that what is sticky in the table — the header and the
 * totals at its edges, the identifying columns at its start — sticks to it; the container
 * takes its own classes and a reference, which the virtualizer of the rows reads. The borders
 * are drawn by the cells, the table keeping them apart: collapsed borders would not follow a
 * sticky cell. No hover colour, no transition.
 */
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** A table: its scrolling container, and the table itself. */
export function Table({
  className,
  container,
  ...props
}: ComponentProps<"table"> & { readonly container?: ComponentProps<"div"> }) {
  const { className: containerClassName, ...containerProps } = container ?? {};
  return (
    <div
      data-slot="table-container"
      className={cn("relative w-full overflow-auto", containerClassName)}
      {...containerProps}
    >
      <table
        data-slot="table"
        className={cn("border-separate border-spacing-0 text-sm", className)}
        {...props}
      />
    </div>
  );
}

/** The header of a table. */
export function TableHeader({ className, ...props }: ComponentProps<"thead">) {
  return <thead data-slot="table-header" className={className} {...props} />;
}

/** The body of a table. */
export function TableBody({ className, ...props }: ComponentProps<"tbody">) {
  return <tbody data-slot="table-body" className={className} {...props} />;
}

/** The footer of a table, where its totals are. */
export function TableFooter({ className, ...props }: ComponentProps<"tfoot">) {
  return <tfoot data-slot="table-footer" className={cn("font-medium", className)} {...props} />;
}

/** A row of a table. */
export function TableRow({ className, ...props }: ComponentProps<"tr">) {
  return <tr data-slot="table-row" className={className} {...props} />;
}

/** A header cell of a table. */
export function TableHead({ className, ...props }: ComponentProps<"th">) {
  return (
    <th
      data-slot="table-head"
      className={cn(
        "border-b px-2 text-left align-middle font-medium whitespace-nowrap text-muted-foreground not-last:border-r",
        className,
      )}
      {...props}
    />
  );
}

/** A cell of a table. */
export function TableCell({ className, ...props }: ComponentProps<"td">) {
  return (
    <td
      data-slot="table-cell"
      className={cn("border-b px-2 align-middle whitespace-nowrap not-last:border-r", className)}
      {...props}
    />
  );
}
