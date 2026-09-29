// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The avatar of shadcn/ui, copied into the repository as far as the shell needs it: the round
 * mark of the account, its initials on the muted token. Without its image: the picture of an
 * account is served by the API (`GET /users/{user_id}/avatar`), which only the server of Next
 * calls — the browser could not load it —, so the image waits for the screen of the account
 * (US-0320).
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
