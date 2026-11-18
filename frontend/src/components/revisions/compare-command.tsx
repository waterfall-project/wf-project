// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * « Comparer à la révision lue », a command of a marked revision of the history (US-2370): a menu of
 * the grids that compare — the planning, the estimate, the remaining to commit — the user may read,
 * each a link to the grid of the revision read with this revision as its base (`base_revision_id`,
 * US-2330). The addresses are built by the screen, by `functionHref`; the texts come translated
 * (défaut n° 12): the component only opens the menu.
 */
"use client";

import { GitCompareArrows } from "lucide-react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

/** A grid the comparison may be read in: its name, and the address that reads it against the base. */
export interface ComparisonGrid {
  readonly key: string;
  readonly label: string;
  readonly href: string;
}

/** What the command says, translated, and the grids it offers. */
export interface CompareCommandProps {
  /** The text of the command, which its accessible name starts with. */
  readonly label: string;
  /** The accessible name, which names the revision compared. */
  readonly name: string;
  readonly grids: readonly ComparisonGrid[];
}

/** Render the command, which opens the menu of the grids offered. */
export function CompareCommand({ label, name, grids }: CompareCommandProps) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="row" size="sm" aria-label={name}>
          <GitCompareArrows aria-hidden="true" />
          {label}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start">
        {grids.map((grid) => (
          <DropdownMenuItem key={grid.key} asChild>
            <Link href={grid.href}>{grid.label}</Link>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
