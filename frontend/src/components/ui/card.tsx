// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The card of shadcn/ui, copied into the repository as far as the screens of the way in and of
 * the account need it: a surface of the card token with a border, its header — a title and what
 * the card is for —, its content and its foot. It lies in the page: no shadow.
 */
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** The surface of a card. */
export function Card({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card"
      className={cn(
        "flex flex-col gap-5 rounded-xl border bg-card py-5 text-card-foreground",
        className,
      )}
      {...props}
    />
  );
}

/** The header of a card: its title, and what it is for. */
export function CardHeader({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card-header"
      className={cn("grid auto-rows-min items-start gap-1.5 px-5", className)}
      {...props}
    />
  );
}

/** The title of a card, a heading of the page at the level it is given. */
export function CardTitle({
  className,
  level: Heading = "h2",
  ...props
}: ComponentProps<"h2"> & { readonly level?: "h1" | "h2" }) {
  return (
    <Heading
      data-slot="card-title"
      className={cn("flex items-center gap-2 leading-none font-semibold", className)}
      {...props}
    />
  );
}

/** What a card is for, under its title. */
export function CardDescription({ className, ...props }: ComponentProps<"p">) {
  return (
    <p
      data-slot="card-description"
      className={cn("text-sm text-muted-foreground", className)}
      {...props}
    />
  );
}

/** The content of a card. */
export function CardContent({ className, ...props }: ComponentProps<"div">) {
  return <div data-slot="card-content" className={cn("px-5", className)} {...props} />;
}

/** The foot of a card, under its content. */
export function CardFooter({ className, ...props }: ComponentProps<"div">) {
  return (
    <div
      data-slot="card-footer"
      className={cn("flex flex-wrap items-center gap-2 px-5", className)}
      {...props}
    />
  );
}
