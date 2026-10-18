// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The alert dialog of shadcn/ui, copied into the repository as far as the confirmation of a deletion
 * needs it (US-0380): a modal dialog of Radix that interrupts the user for a decision — named by its
 * title, described by its description —, which takes the focus to its cancellation as it opens, holds
 * it there, and closes on Escape or on either of its commands, never by a press outside it. The
 * surface of the background token, a border and the one shadow of the charter, centred over the page;
 * neither overlay — no token was measured for a scrim — nor animation, as the dialog of the paste.
 */
"use client";

import { AlertDialog as AlertDialogPrimitive } from "radix-ui";
import type { ComponentProps } from "react";

import { buttonVariants } from "./button";
import { cn } from "./utils";

/** An alert dialog: open or closed, and its content. */
export function AlertDialog(props: ComponentProps<typeof AlertDialogPrimitive.Root>) {
  return <AlertDialogPrimitive.Root data-slot="alert-dialog" {...props} />;
}

/** The content of an alert dialog, over the page, at its centre. */
export function AlertDialogContent({
  className,
  ...props
}: ComponentProps<typeof AlertDialogPrimitive.Content>) {
  return (
    <AlertDialogPrimitive.Portal>
      <AlertDialogPrimitive.Content
        data-slot="alert-dialog-content"
        className={cn(
          "fixed top-1/2 left-1/2 z-50 grid w-full max-w-lg -translate-1/2 gap-4 rounded-lg border bg-background p-6 shadow-md outline-hidden",
          className,
        )}
        {...props}
      />
    </AlertDialogPrimitive.Portal>
  );
}

/** The heading of an alert dialog: its title and its description. */
export function AlertDialogHeader({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-dialog-header"
      className={cn("flex flex-col gap-1.5", className)}
      {...props}
    />
  );
}

/** The foot of an alert dialog, where its commands stand. */
export function AlertDialogFooter({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="alert-dialog-footer"
      className={cn("flex flex-wrap justify-end gap-2", className)}
      {...props}
    />
  );
}

/** The title of an alert dialog, which names it. */
export function AlertDialogTitle({
  className,
  ...props
}: ComponentProps<typeof AlertDialogPrimitive.Title>) {
  return (
    <AlertDialogPrimitive.Title
      data-slot="alert-dialog-title"
      className={cn("text-lg font-semibold text-foreground", className)}
      {...props}
    />
  );
}

/** The description of an alert dialog, which describes it. */
export function AlertDialogDescription({
  className,
  ...props
}: ComponentProps<typeof AlertDialogPrimitive.Description>) {
  return (
    <AlertDialogPrimitive.Description
      data-slot="alert-dialog-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  );
}

/** The command that confirms what the dialog asks, and closes it. */
export function AlertDialogAction({
  className,
  ...props
}: ComponentProps<typeof AlertDialogPrimitive.Action>) {
  return (
    <AlertDialogPrimitive.Action
      data-slot="alert-dialog-action"
      className={cn(buttonVariants({ size: "sm" }), className)}
      {...props}
    />
  );
}

/** The command that gives up what the dialog asks, and closes it. */
export function AlertDialogCancel({
  className,
  ...props
}: ComponentProps<typeof AlertDialogPrimitive.Cancel>) {
  return (
    <AlertDialogPrimitive.Cancel
      data-slot="alert-dialog-cancel"
      className={cn(buttonVariants({ variant: "outline", size: "sm" }), className)}
      {...props}
    />
  );
}
