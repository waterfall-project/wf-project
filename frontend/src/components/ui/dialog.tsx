// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The dialog of shadcn/ui, copied into the repository as far as the confirmation of a paste needs
 * it (WF-IHM-0050): a modal dialog of Radix, named by its title and described by its description,
 * which takes the focus into it as it opens, holds it there, closes on Escape and gives the focus
 * back to what had it. The surface of the background token, a border and the one shadow of the
 * charter, centred over the page; neither overlay — no token was measured for a scrim — nor
 * animation, and no close button: the dialog offers its own way out.
 */
"use client";

import { Dialog as DialogPrimitive } from "radix-ui";
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** A dialog: open or closed, and its content. */
export function Dialog(props: ComponentProps<typeof DialogPrimitive.Root>) {
  return <DialogPrimitive.Root data-slot="dialog" {...props} />;
}

/** The content of a dialog, over the page, at its centre. */
export function DialogContent({
  className,
  ...props
}: ComponentProps<typeof DialogPrimitive.Content>) {
  return (
    <DialogPrimitive.Portal>
      <DialogPrimitive.Content
        data-slot="dialog-content"
        className={cn(
          "fixed top-1/2 left-1/2 z-50 grid max-h-[90svh] w-full max-w-lg -translate-1/2 gap-4 overflow-y-auto rounded-lg border bg-background p-6 shadow-md outline-hidden",
          className,
        )}
        {...props}
      />
    </DialogPrimitive.Portal>
  );
}

/** The heading of a dialog: its title and its description. */
export function DialogHeader({ className, ...props }: ComponentProps<"div">) {
  return (
    <div data-slot="dialog-header" className={cn("flex flex-col gap-1.5", className)} {...props} />
  );
}

/** The foot of a dialog, where its commands stand. */
export function DialogFooter({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="dialog-footer"
      className={cn("flex flex-wrap justify-end gap-2", className)}
      {...props}
    />
  );
}

/** The title of a dialog, which names it. */
export function DialogTitle({ className, ...props }: ComponentProps<typeof DialogPrimitive.Title>) {
  return (
    <DialogPrimitive.Title
      data-slot="dialog-title"
      className={cn("text-lg font-semibold text-foreground", className)}
      {...props}
    />
  );
}

/** The description of a dialog, which describes it. */
export function DialogDescription({
  className,
  ...props
}: ComponentProps<typeof DialogPrimitive.Description>) {
  return (
    <DialogPrimitive.Description
      data-slot="dialog-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  );
}
