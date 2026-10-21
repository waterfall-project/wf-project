// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The structure a grid of a revision reads (US-0500), as the address names it: `structure`, the
 * identifier of one of the structures the revision lists (`listCostStructures`) — the main one, a
 * differential that prepares an amendment, the own estimate of a risk —, the main one when the
 * address names none. The planning and the estimate read the structure named (`grid-screen.ts`);
 * the remaining to commit, the main one alone (WF-RAE-0040). The banner of the reading context
 * names the structure read and offers the others of the revision, in the order the server lists
 * them (WF-IHM-0020, WF-REV-0100).
 *
 * Pure, and neither server nor client: the page reads the address, the choice writes it.
 */
import type { components } from "@/api/generated/schema";
import { filterHref } from "@/components/grid/filters";

/** The parameter of the address that names the structure a grid reads. */
export const STRUCTURE_PARAMETER = "structure";

/** What a structure is: the main one, a differential of an amendment, the own estimate of a risk. */
export type StructureKind = components["schemas"]["StructureKind"];

/** A structure of the revision, as the banner names it and offers it. */
export interface ListedStructure {
  readonly structure_id: string;
  readonly label: string;
  readonly kind: StructureKind;
  readonly is_merged: boolean;
}

/** The structure a grid reads, and every structure of its revision, as the server lists them. */
export interface StructureChoices {
  readonly read: ListedStructure;
  readonly listed: readonly ListedStructure[];
}

/** What the banner names of a structure, and what crosses to the browser of it: nothing more. */
export function listedStructure({
  structure_id,
  label,
  kind,
  is_merged,
}: ListedStructure): ListedStructure {
  return { structure_id, label, kind, is_merged };
}

/**
 * The structures of a kind that follow one another, in the order the server lists them — the main
 * one, the differentials, the own estimates of the risks —, never reordered: a kind that comes back
 * later starts a run of its own.
 */
export function runsOfKind(
  listed: readonly ListedStructure[],
): { readonly kind: StructureKind; readonly structures: readonly ListedStructure[] }[] {
  const runs: { kind: StructureKind; structures: ListedStructure[] }[] = [];
  for (const structure of listed) {
    const last = runs.at(-1);
    if (last?.kind === structure.kind) {
      last.structures.push(structure);
    } else {
      runs.push({ kind: structure.kind, structures: [structure] });
    }
  }
  return runs;
}

/**
 * The address of the same screen on a structure, the rest of its query kept — the search, the
 * sort, the filters —: the main structure lifts the parameter, the address naming none reading it.
 */
export function structureHref(
  pathname: string,
  query: URLSearchParams,
  structure: Pick<ListedStructure, "structure_id" | "kind">,
): string {
  return filterHref(
    pathname,
    query,
    STRUCTURE_PARAMETER,
    structure.kind === "main" ? undefined : structure.structure_id,
  );
}

/**
 * An address of the same screen that keeps the structure read: a filter of the context lifted by
 * the banner leaves the grid on the structure it reads, rather than taking it back to the main one.
 */
export function keepingStructure(href: string, choices: StructureChoices | undefined): string {
  if (choices === undefined) {
    return href;
  }
  const [pathname = "", query = ""] = href.split("?", 2);
  return structureHref(pathname, new URLSearchParams(query), choices.read);
}
