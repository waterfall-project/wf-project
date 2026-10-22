// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The link that lifts a filter from the banner of the reading context (WF-IHM-0020): the address of
 * the same screen without the filter, which the page computed (`href`, for a new tab or a window), and
 * which a plain click does not follow as it is. It goes on from the address last asked
 * (`usePendingAddress`), which the screen shares between its banner and its grid (`PendingAddress`):
 * the parameters that carry the filter lifted from it, the rest of its query kept — the search, the
 * sort asked and not yet arrived, the structure read —, so that a sort asked before the filter is
 * lifted survives it, and the reverse (défaut n° 20 de `typescript.md`, #1221).
 *
 * Every prop is data, never a function: the banner, a server component, hands it over (défaut n° 12).
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { MouseEvent, ReactNode } from "react";

import { filterHref } from "@/components/grid/filters";
import { usePendingAddress } from "@/components/grid/pending-address";

/** What lifts a filter: its address, the parameters that carry it, and what names the link. */
export interface ChipLiftProps {
  /** The address of the screen without the filter. */
  readonly href: string;
  /** The parameters of the address the filter is read from: all are lifted. */
  readonly lifts: readonly string[];
  /** The accessible name of the link, which names the filter lifted. */
  readonly label: string;
  readonly children: ReactNode;
}

/** Render the link that lifts a filter. */
export function ChipLift({ href, lifts, label, children }: ChipLiftProps) {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const lift = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }
    event.preventDefault();
    request((query) => filterHref(pathname, query, lifts[0] ?? "", undefined, lifts.slice(1)));
  };
  return (
    <Link
      href={href}
      onClick={lift}
      aria-label={label}
      className="rounded-full p-0.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-[3px] focus-visible:ring-ring"
    >
      {children}
    </Link>
  );
}
