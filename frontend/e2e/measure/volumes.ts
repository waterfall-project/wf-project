// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The reads of the measure at volumes (US-2970/L2), by the operations of the contract, as the user
 * of the measure makes them: the revisions of PRJ-001 the platform holds, the revision read in full
 * (the structure and its nodes, as the grids read it: WF-DAT-0050-A), and the indicators kept at a
 * past date (WF-DAT-0040). The durations are those of `scale.ts`.
 */
import type { components } from "../../src/api/generated/schema";
import type { Caller } from "./background";
import { type ReadingSummary, timeReads } from "./scale";

type Schemas = components["schemas"];

/** A revision of a project, as far as the measure reads it. */
export interface RevisionRef {
  readonly revision_id: string;
  readonly status: Schemas["Revision"]["status"];
  readonly marked_at: string | null;
}

/** The most a page of a list holds (the contract). */
const PAGE = 500;

/** Every revision of a project, the most recent first, page after page. */
export async function revisionsOf(api: Caller, project: string): Promise<RevisionRef[]> {
  const found: RevisionRef[] = [];
  for (let offset = 0; ; offset += PAGE) {
    const page = await api.get<{ items: RevisionRef[]; meta: { total: number } }>(
      `/projects/${project}/revisions?limit=${String(PAGE)}&offset=${String(offset)}`,
    );
    found.push(...page.items);
    if (found.length >= page.meta.total || page.items.length === 0) {
      return found;
    }
  }
}

/** The current revision of a project: the one in progress, which the grids open on. */
export function currentOf(revisions: readonly RevisionRef[]): string {
  const current = revisions.find(({ status }) => status === "draft");
  if (current === undefined) {
    throw new Error("the project holds no revision in progress to measure");
  }
  return current.revision_id;
}

/** The marked revisions, the oldest first. */
export function markedOf(revisions: readonly RevisionRef[]): RevisionRef[] {
  return revisions
    .filter(({ status }) => status === "marked")
    .toSorted((a, b) => (a.marked_at ?? "").localeCompare(b.marked_at ?? ""));
}

/** `count` items spread over a list, the first and the last among them (all if it is shorter). */
export function spread<T>(items: readonly T[], count: number): T[] {
  if (items.length <= count) {
    return [...items];
  }
  return Array.from({ length: count }, (_, index) => {
    const at = Math.round((index * (items.length - 1)) / (count - 1));
    return items[at] as T;
  });
}

/** The day of an instant, as the contract writes a date. */
export function dayOf(instant: string): string {
  return instant.slice(0, 10);
}

/**
 * The marked revisions read in full: the nodes of their main structure, one read each, as a grid
 * reads them. Named by the revision, so that two platforms are compared on the same ones.
 */
export async function revisionReads(
  api: Caller,
  project: string,
  revisions: readonly string[],
  passes: number,
): Promise<ReadingSummary[]> {
  const reads: ReadingSummary[] = [];
  for (const revision of revisions) {
    const structures = await api.get<Schemas["CostStructure"][]>(
      `/projects/${project}/revisions/${revision}/structures`,
    );
    const main = structures.find((structure) => structure.kind === "main");
    if (main === undefined) {
      throw new Error(`the revision ${revision} has no main structure`);
    }
    reads.push(
      await timeReads(
        api,
        `revision ${revision}`,
        `/projects/${project}/revisions/${revision}/structures/${main.structure_id}/nodes`,
        passes,
      ),
    );
  }
  return reads;
}

/**
 * The indicators kept at the past date of the marking of each of the revisions given: the reading
 * of a past date, which the back answers from what the revision kept (WF-DAT-0040), never by
 * computing it anew.
 */
export async function keptReads(
  api: Caller,
  project: string,
  revisions: readonly RevisionRef[],
  passes: number,
): Promise<ReadingSummary[]> {
  const reads: ReadingSummary[] = [];
  for (const { marked_at: markedAt } of revisions) {
    if (markedAt === null) {
      throw new Error("a marked revision has the instant of its marking");
    }
    const day = dayOf(markedAt);
    reads.push(
      await timeReads(
        api,
        `indicators kept at ${day}`,
        `/projects/${project}/indicators?as_of=${day}`,
        passes,
      ),
    );
  }
  return reads;
}

/** How many projects a platform lists (`meta.total` of `listProjects`). */
export async function projectCount(api: Caller): Promise<number> {
  const page = await api.get<{ meta: { total: number } }>("/projects?limit=1");
  return page.meta.total;
}
