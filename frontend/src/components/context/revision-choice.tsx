// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The choice of a revision, in the banner of the reading context (US-2330, WF-IHM-0020): a button,
 * as narrow as an icon, whose accessible name says the revision chosen, and that opens a menu of the
 * revisions offered in the order the server lists them, the one chosen checked — as the choice of
 * the structure (`StructureChoice`). By the pointer as by the keyboard: the button opens the menu at
 * Enter, Space or the down arrow, the arrows go from one revision to the next, Enter chooses.
 *
 * `RevisionMenu` is the menu alone, which leaves to its caller what a choice does: the revision read
 * (`ReadRevisionChoice`), the base of a comparison. A choice only changes the address, from the
 * address last asked (`usePendingAddress`), shared by the screen between its banner and its grid
 * (`PendingAddress`): a filter of the sub-project chosen just before is kept (défaut n° 20 de
 * `typescript.md`); the menu shows the revision chosen checked until the page read anew arrives
 * (défaut n° 21).
 *
 * Every prop of `ReadRevisionChoice` is data, the texts given translated: the banner, a server
 * component, hands it over (défaut n° 12).
 */
"use client";

import { History } from "lucide-react";
import { usePathname } from "next/navigation";
import { type ReactNode, useOptimistic, useTransition } from "react";

import { usePendingAddress } from "@/components/grid/pending-address";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import { revisionHref } from "./revision";

/** A revision offered, by its identifier and the text that names it. */
export interface RevisionOption {
  readonly revision_id: string;
  readonly text: string;
}

/** What a choice of a revision offers, and which revision it shows chosen. */
export interface RevisionChoiceProps {
  /** The accessible name of the button, which names the revision chosen. */
  readonly label: string;
  /** The revisions offered, in the order the server lists them. */
  readonly options: readonly RevisionOption[];
  /** The revision chosen; none checked when none is. */
  readonly chosen: string | undefined;
}

/** What the menu alone takes besides: what a choice does, and what it offers after the revisions. */
export interface RevisionMenuProps extends RevisionChoiceProps {
  /** Ask the address of the revision chosen; called in the transition that shows it checked. */
  readonly onChoose: (revisionId: string) => void;
  /** Items offered after the revisions — lifting a choice made —, if any. */
  readonly children?: ReactNode;
}

/**
 * Render a menu of revisions, the one chosen checked from the choice made until it arrives; the one
 * shown chosen again asks nothing.
 */
export function RevisionMenu({ label, options, chosen, onChoose, children }: RevisionMenuProps) {
  const [shown, show] = useOptimistic(chosen);
  const [, startTransition] = useTransition();
  const choose = (revisionId: string) => {
    // The revision shown chosen again asks nothing: the screen already reads it, or is on its way.
    if (revisionId === shown) {
      return;
    }
    startTransition(() => {
      show(revisionId);
      onChoose(revisionId);
    });
  };
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="ghost" className="size-6 p-0" aria-label={label}>
          <History aria-hidden="true" className="size-3.5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-80">
        <DropdownMenuRadioGroup value={shown ?? ""}>
          {options.map((option) => (
            <DropdownMenuRadioItem
              key={option.revision_id}
              value={option.revision_id}
              onSelect={() => {
                choose(option.revision_id);
              }}
            >
              {option.text}
            </DropdownMenuRadioItem>
          ))}
        </DropdownMenuRadioGroup>
        {children}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

/**
 * Render the choice of the revision a screen reads: the revision chosen opens on the same screen,
 * the sub-project and the date of calculation kept (`revisionHref`).
 */
export function ReadRevisionChoice(props: RevisionChoiceProps) {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  return (
    <RevisionMenu
      {...props}
      onChoose={(revisionId) => {
        request((query) => revisionHref(pathname, query, revisionId));
      }}
    />
  );
}
