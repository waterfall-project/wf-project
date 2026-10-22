// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The link that lifts a filter from the banner of the reading context (WF-IHM-0020): the address of
 * the screen without the parameters that carry the filter, built from the query as the grid reads it
 * (`usePendingLink`). Its `href`, for a new tab or a window, goes on from the address shown; a plain
 * click goes on from the address last asked (`usePendingAddress`), which the screen shares between
 * its banner and its grid (`PendingAddress`) — the whole query kept but for the filter lifted: the
 * search, the sort asked and not yet arrived, the structure read —, so that a sort asked before the
 * filter is lifted survives it, and the reverse (défaut n° 20 de `typescript.md`, #1221). The same
 * calculation gives the `href` and the click.
 *
 * Every prop is data, never a function: the banner, a server component, hands it over (défaut n° 12).
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { withoutParameters } from "@/components/grid/filters";
import { usePendingLink } from "@/components/grid/pending-address";

/** What lifts a filter: its address, the parameters that carry it, and what names the link. */
export interface ChipLiftProps {
  /** The parameters of the address the filter is read from: all are lifted. */
  readonly lifts: readonly string[];
  /** The accessible name of the link, which names the filter lifted. */
  readonly label: string;
  readonly children: ReactNode;
}

/** Render the link that lifts a filter. */
export function ChipLift({ lifts, label, children }: ChipLiftProps) {
  const pathname = usePathname();
  const { href, onClick } = usePendingLink((query) => withoutParameters(pathname, query, lifts));
  return (
    <Link
      href={href}
      onClick={onClick}
      aria-label={label}
      className="rounded-full p-0.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring"
    >
      {children}
    </Link>
  );
}
