// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The sheet of shadcn/ui, copied into the repository as far as the side bar needs it: on a
 * narrow screen, the side bar slides over the page from its edge, a dialog of Radix — the
 * focus held within it, Escape or a press outside closing it and giving the focus back.
 * Neither overlay nor close button: the page stays in sight beside it, without a scrim no
 * token was measured for, and the trigger of the bar closes it as it opened it.
 */
"use client";

import { Dialog as SheetPrimitive } from "radix-ui";
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** A sheet: open or closed, and its content. */
export function Sheet(props: ComponentProps<typeof SheetPrimitive.Root>) {
  return <SheetPrimitive.Root data-slot="sheet" {...props} />;
}

/** The content of a sheet, along the left edge of the window, where the side bar lives. */
export function SheetContent({
  className,
  ...props
}: ComponentProps<typeof SheetPrimitive.Content>) {
  return (
    <SheetPrimitive.Portal>
      <SheetPrimitive.Content
        data-slot="sheet-content"
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex h-full flex-col border-r bg-background",
          className,
        )}
        {...props}
      />
    </SheetPrimitive.Portal>
  );
}

/** The heading of a sheet: its title and its description. */
export function SheetHeader({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="sheet-header"
      className={cn("flex flex-col gap-1.5 p-4", className)}
      {...props}
    />
  );
}

/** The title of a sheet, which names its dialog. */
export function SheetTitle({ className, ...props }: ComponentProps<typeof SheetPrimitive.Title>) {
  return (
    <SheetPrimitive.Title
      data-slot="sheet-title"
      className={cn("font-semibold text-foreground", className)}
      {...props}
    />
  );
}

/** The description of a sheet, which describes its dialog. */
export function SheetDescription({
  className,
  ...props
}: ComponentProps<typeof SheetPrimitive.Description>) {
  return (
    <SheetPrimitive.Description
      data-slot="sheet-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  );
}
