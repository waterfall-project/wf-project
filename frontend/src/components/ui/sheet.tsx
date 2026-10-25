// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The sheet of shadcn/ui, copied into the repository as far as the shell needs it: on a narrow
 * screen, the side bar slides over the page from its left edge; the panel of the tasks and the
 * messages, from the right (`TaskPanel`). A dialog of Radix — the focus held within it, Escape or a
 * press outside closing it and giving the focus back. No overlay: the page stays in sight beside it,
 * without a scrim no token was measured for. The side bar has no close button, the trigger of the
 * bar closing it as it opened it; the panel has its own.
 */
"use client";

import { Dialog as SheetPrimitive } from "radix-ui";
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** A sheet: open or closed, and its content. */
export function Sheet(props: ComponentProps<typeof SheetPrimitive.Root>) {
  return <SheetPrimitive.Root data-slot="sheet" {...props} />;
}

/** The edge a sheet lies along, by its classes. */
const SIDES = {
  left: "left-0 border-r",
  right: "right-0 border-l",
} as const;

/**
 * The content of a sheet, along an edge of the window: the left by default, where the side bar
 * lives.
 */
export function SheetContent({
  className,
  side = "left",
  ...props
}: ComponentProps<typeof SheetPrimitive.Content> & { readonly side?: keyof typeof SIDES }) {
  return (
    <SheetPrimitive.Portal>
      <SheetPrimitive.Content
        data-slot="sheet-content"
        className={cn(
          "fixed inset-y-0 z-50 flex h-full flex-col bg-background",
          SIDES[side],
          className,
        )}
        {...props}
      />
    </SheetPrimitive.Portal>
  );
}

/** What closes a sheet, given as its child — a button. */
export function SheetClose(props: ComponentProps<typeof SheetPrimitive.Close>) {
  return <SheetPrimitive.Close data-slot="sheet-close" {...props} />;
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
