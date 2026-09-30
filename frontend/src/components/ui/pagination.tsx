// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The pagination of shadcn/ui, copied into the repository for the list of projects: a
 * navigation, named by its caller from the catalogue, whose links lead to other pages of a list.
 * The links are those of Next, and the words of the previous and next pages are the caller's —
 * shadcn writes them in English. What no screen employs, the ellipsis, is not copied.
 */
import { ChevronLeft, ChevronRight } from "lucide-react";
import Link from "next/link";
import type { ComponentProps } from "react";

import { buttonVariants } from "./button";
import { cn } from "./utils";

/** A pagination: a navigation, named by its caller. */
export function Pagination({ className, ...props }: ComponentProps<"nav">) {
  return <nav data-slot="pagination" className={cn("flex", className)} {...props} />;
}

/** The links of a pagination, in order. */
export function PaginationContent({ className, ...props }: ComponentProps<"ul">) {
  return (
    <ul
      data-slot="pagination-content"
      className={cn("flex flex-row items-center gap-1", className)}
      {...props}
    />
  );
}

/** A place in a pagination. */
export function PaginationItem(props: ComponentProps<"li">) {
  return <li data-slot="pagination-item" {...props} />;
}

/** A link of a pagination: the link of Next, drawn as a button of the charter. */
export function PaginationLink({ className, ...props }: ComponentProps<typeof Link>) {
  return (
    <Link
      data-slot="pagination-link"
      className={cn(buttonVariants({ variant: "outline", size: "sm" }), className)}
      {...props}
    />
  );
}

/** The link to the previous page, its words given by the caller. */
export function PaginationPrevious({ children, ...props }: ComponentProps<typeof Link>) {
  return (
    <PaginationLink {...props}>
      <ChevronLeft aria-hidden="true" />
      {children}
    </PaginationLink>
  );
}

/** The link to the next page, its words given by the caller. */
export function PaginationNext({ children, ...props }: ComponentProps<typeof Link>) {
  return (
    <PaginationLink {...props}>
      {children}
      <ChevronRight aria-hidden="true" />
    </PaginationLink>
  );
}
