// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The avatar of shadcn/ui, copied into the repository: the round mark of the account, its image
 * or, until the image is loaded or without one, its initials on the muted token. The image of an
 * account is served by the API (`getUserAvatar`), which only the server of Next calls: the
 * screen of the avatar writes it into the page as a `data:` address (`avatar-source.ts`); the
 * menu of the account shows the initials.
 */
"use client";

import { Avatar as AvatarPrimitive } from "radix-ui";
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** The round frame of an avatar. */
export function Avatar({ className, ...props }: ComponentProps<typeof AvatarPrimitive.Root>) {
  return (
    <AvatarPrimitive.Root
      data-slot="avatar"
      className={cn(
        "relative flex size-7 shrink-0 overflow-hidden rounded-full select-none",
        className,
      )}
      {...props}
    />
  );
}

/** The image of an avatar, shown once the browser has loaded it. */
export function AvatarImage({ className, ...props }: ComponentProps<typeof AvatarPrimitive.Image>) {
  return (
    <AvatarPrimitive.Image
      data-slot="avatar-image"
      className={cn("aspect-square size-full object-cover", className)}
      {...props}
    />
  );
}

/** What an avatar shows without its image: the initials of the account. */
export function AvatarFallback({
  className,
  ...props
}: ComponentProps<typeof AvatarPrimitive.Fallback>) {
  return (
    <AvatarPrimitive.Fallback
      data-slot="avatar-fallback"
      className={cn(
        "flex size-full items-center justify-center rounded-full bg-muted text-xs font-semibold text-foreground",
        className,
      )}
      {...props}
    />
  );
}
