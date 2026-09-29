// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The breadcrumb of shadcn/ui, copied into the repository: where the page shown sits, in the
 * bar of the shell, each step before it a link. The navigation is named by its caller, from
 * the catalogue; the page shown is marked `aria-current` and is no link — shadcn gives it the
 * role of a disabled link, which a screen reader would offer to follow.
 */
import { ChevronRight } from "lucide-react";
import Link from "next/link";
import type { ComponentProps } from "react";

import { cn } from "./utils";

/** A breadcrumb: a navigation, named by its caller. */
export function Breadcrumb(props: ComponentProps<"nav">) {
  return <nav data-slot="breadcrumb" {...props} />;
}

/** The steps of a breadcrumb, in order. */
export function BreadcrumbList({ className, ...props }: ComponentProps<"ol">) {
  return (
    <ol
      data-slot="breadcrumb-list"
      className={cn(
        "flex min-w-0 flex-wrap items-center gap-1.5 text-sm break-words text-muted-foreground",
        className,
      )}
      {...props}
    />
  );
}

/** A step of a breadcrumb. */
export function BreadcrumbItem({ className, ...props }: ComponentProps<"li">) {
  return (
    <li
      data-slot="breadcrumb-item"
      className={cn("inline-flex min-w-0 items-center gap-1.5", className)}
      {...props}
    />
  );
}

/** A step before the page shown: a link to it. */
export function BreadcrumbLink({ className, ...props }: ComponentProps<typeof Link>) {
  return (
    <Link
      data-slot="breadcrumb-link"
      className={cn("truncate rounded-sm hover:text-foreground", className)}
      {...props}
    />
  );
}

/** The step of the page shown, or of a place without a page of its own. */
export function BreadcrumbPage({ className, ...props }: ComponentProps<"span">) {
  return (
    <span
      data-slot="breadcrumb-page"
      className={cn("truncate text-foreground", className)}
      {...props}
    />
  );
}

/** The mark between two steps, hidden from a screen reader: the list says the order. */
export function BreadcrumbSeparator({ className, ...props }: ComponentProps<"li">) {
  return (
    <li
      data-slot="breadcrumb-separator"
      role="presentation"
      aria-hidden="true"
      className={cn("shrink-0 [&>svg]:size-3.5", className)}
      {...props}
    >
      <ChevronRight />
    </li>
  );
}
