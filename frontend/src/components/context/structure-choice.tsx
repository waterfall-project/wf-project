// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The choice of the structure a grid reads, in the banner of its reading context (US-0500,
 * WF-IHM-0020): a button, as narrow as an icon, that names the structure read and opens a menu of
 * the structures of the revision in the order the server lists them, those of a kind that follow
 * one another under the name of their kind, the one read checked. On a narrow window the banner
 * wraps onto a second row, and the page scrolls when the window is too low for the floor of the
 * grid under it (US-0560). A choice only changes the address (`structureHref`), the rest of its
 * query kept, from the address last asked (`usePendingAddress`) — which the screen shares between
 * its banner and its grid (`PendingAddress`), so that a sort asked before the structure arrives keeps it, and the reverse
 * (défaut n° 20 de `typescript.md`); the page reads the grid anew on the structure chosen, which the
 * menu shows checked meanwhile (défaut n° 21).
 *
 * Every prop is data, the texts given translated, never a function: the banner, a server component,
 * hands it over (défaut n° 12).
 */
"use client";

import { ChevronsUpDown } from "lucide-react";
import { usePathname } from "next/navigation";
import { type ReactNode, useId, useOptimistic, useTransition } from "react";

import { usePendingAddress } from "@/components/grid/pending-address";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

import { type ListedStructure, structureHref } from "./structure";

/** A structure offered, by its identifier, its kind and the text that names it. */
export interface StructureOption extends Pick<ListedStructure, "structure_id" | "kind"> {
  readonly text: string;
}

/**
 * Structures of a kind that follow one another in the order of the server, under the name of their
 * kind; none for the main structure, which its own label names.
 */
export interface StructureGroup {
  readonly name: string | undefined;
  readonly options: readonly StructureOption[];
}

/** A run of structures of a kind, named by its kind when it has a name. */
function Group({
  group,
  children,
}: {
  readonly group: StructureGroup;
  readonly children: ReactNode;
}) {
  const label = useId();
  if (group.name === undefined) {
    return <>{children}</>;
  }
  return (
    <DropdownMenuGroup aria-labelledby={label}>
      <DropdownMenuLabel id={label} className="text-xs text-muted-foreground">
        {group.name}
      </DropdownMenuLabel>
      {children}
    </DropdownMenuGroup>
  );
}

/** What the choice offers: the structures of the revision, the one read, and its button's name. */
export interface StructureChoiceProps {
  /** The accessible name of the button, which names the structure read. */
  readonly label: string;
  readonly groups: readonly StructureGroup[];
  /** The structure read. */
  readonly chosen: string;
}

/** Render the choice of the structure a grid reads, the one read checked. */
export function StructureChoice({ label, groups, chosen }: StructureChoiceProps) {
  const pathname = usePathname();
  const { request } = usePendingAddress();
  const [shown, show] = useOptimistic(chosen);
  const [, startTransition] = useTransition();
  const choose = (option: StructureOption) => {
    startTransition(() => {
      show(option.structure_id);
      request((query) => structureHref(pathname, query, option));
    });
  };
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" variant="ghost" className="size-6 p-0" aria-label={label}>
          <ChevronsUpDown aria-hidden="true" className="size-3.5" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="start" className="w-80">
        <DropdownMenuRadioGroup value={shown}>
          {groups.map((group) => (
            // A run is known by its first structure: one kind may come back later in the list.
            <Group key={group.options[0]?.structure_id} group={group}>
              {group.options.map((option) => (
                <DropdownMenuRadioItem
                  key={option.structure_id}
                  value={option.structure_id}
                  onSelect={() => {
                    choose(option);
                  }}
                >
                  {option.text}
                </DropdownMenuRadioItem>
              ))}
            </Group>
          ))}
        </DropdownMenuRadioGroup>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
