// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the imports and exports offers, which both its server and its client parts read: the
 * import and the export of each kind of file, as the server offers its command (WF-IHM-0090); what
 * an import still lets the user do, by its status; and the address of the report of an import.
 *
 * An import is a command of the project — `import_planning`, `import_estimate`,
 * `import_remaining`, `import_actual_costs` —, offered with or without a current revision, which
 * the import writes into or creates (WF-INTF-0090); an export, a command of the revision it reads
 * — `export_planning`, `export_estimate`, `export_remaining`, `export_task_tree_image`. The front
 * deduces nothing from a permission, nor from the entry of the revision.
 */
import type { components } from "@/api/generated/schema";
import { type CommandOffer, findOffer } from "@/components/commands/offer";
import type { Project } from "@/components/context/reading";
import type { Revision } from "@/components/context/read-only";
import { OFFSET } from "@/components/grid/query";
import type { PagedList } from "@/navigation/pages";

type ExchangeKind = components["schemas"]["ExchangeKind"];
type ExportKind = components["schemas"]["ExportRequest"]["kind"];
type ImportStatus = components["schemas"]["Import"]["status"];
type ProjectCommand = components["schemas"]["ProjectCommand"];
type RevisionCommand = components["schemas"]["RevisionCommand"];

/** The kinds of file an import reads, in the order of the flows (FLX-01 to FLX-07). */
export const EXCHANGE_KINDS: readonly ExchangeKind[] = [
  "ms_project_schedule",
  "estimate",
  "remaining",
  "actual_costs",
];

/** The kinds of file an export makes, in the order of the contract. */
export const EXPORT_KINDS: readonly ExportKind[] = [
  "ms_project_schedule",
  "estimate",
  "remaining",
  "task_tree_image",
];

/** The command of the project that imports each kind of file. */
export const IMPORT_COMMAND: Readonly<Record<ExchangeKind, ProjectCommand>> = {
  ms_project_schedule: "import_planning",
  estimate: "import_estimate",
  remaining: "import_remaining",
  actual_costs: "import_actual_costs",
};

/** The command of the revision that exports each kind of file. */
const EXPORT_COMMAND: Readonly<Record<ExportKind, RevisionCommand>> = {
  ms_project_schedule: "export_planning",
  estimate: "export_estimate",
  remaining: "export_remaining",
  task_tree_image: "export_task_tree_image",
};

/** The import of each kind, as the server offers it; `undefined` where it is not offered. */
export type ImportOffers = Readonly<Record<ExchangeKind, CommandOffer | undefined>>;

/** The export of each kind, as the server offers it; `undefined` where it is not offered. */
export type ExportOffers = Readonly<Record<ExportKind, CommandOffer | undefined>>;

/** What the project offers of each import, whether it has a current revision or not. */
export function importOffers(project: Project): ImportOffers {
  const offer = (kind: ExchangeKind) => findOffer(project.available_commands, IMPORT_COMMAND[kind]);
  return {
    ms_project_schedule: offer("ms_project_schedule"),
    estimate: offer("estimate"),
    remaining: offer("remaining"),
    actual_costs: offer("actual_costs"),
  };
}

/**
 * Whether the project lists an import at all, available or not: the caller has the permission of
 * one, which the screen of the imports and exports exercises. With the read of the planning, what
 * guards that screen (#521): a costing engineer who does not read the planning reaches it by the
 * import of the estimate or of the remaining to commit, which the project lists to them.
 */
export function listsAnImport(project: Project): boolean {
  return Object.values(importOffers(project)).some((offer) => offer !== undefined);
}

/**
 * Whether the project lists the import of a kind of file, available or not: the screen of its
 * function then leads to the screen of the imports and exports, which offers it, or presents it
 * unavailable with the conditions it lacks (#521, WF-IHM-0090).
 */
export function listsImport(project: Project, kind: ExchangeKind): boolean {
  return importOffers(project)[kind] !== undefined;
}

/** What the revision read offers of each export; none without a revision. */
export function exportOffers(revision: Revision | undefined): ExportOffers {
  const offer = (kind: ExportKind) =>
    revision === undefined
      ? undefined
      : findOffer(revision.available_commands, EXPORT_COMMAND[kind]);
  return {
    ms_project_schedule: offer("ms_project_schedule"),
    estimate: offer("estimate"),
    remaining: offer("remaining"),
    task_tree_image: offer("task_tree_image"),
  };
}

/**
 * Whether an import, by its status, may still be applied — its report analysed, awaiting the
 * decision of the user — or abandoned — still open. Every status of the contract is named: one
 * the contract adds fails the type check until it is classified here.
 */
export const IMPORT_STEPS: Readonly<
  Record<ImportStatus, { readonly apply: boolean; readonly abandon: boolean }>
> = {
  analysing: { apply: false, abandon: true },
  analysed: { apply: true, abandon: true },
  applying: { apply: false, abandon: false },
  applied: { apply: false, abandon: false },
  abandoned: { apply: false, abandon: false },
  expired: { apply: false, abandon: false },
  failed: { apply: false, abandon: false },
};

/** A mebibyte, in bytes. */
export const MEBIBYTE = 1024 * 1024;

/**
 * The largest file an import takes, as the contract bounds a deposit for an import (`uploadFile`,
 * `purpose: import`): 10 MiB, an MS Project file, the largest the volumes of §4.6.2 name. The
 * bound of the server actions of Next (`next.config.ts`) is set a little above it.
 */
export const IMPORT_MAX_BYTES = 10 * MEBIBYTE;

/** The parameter of the address that names the page of the imports of the project. */
export const EXCHANGES_PAGE = OFFSET;

/** The imports of a project, which read nothing of the address but their page. */
export const EXCHANGES_LIST: PagedList = { page: EXCHANGES_PAGE, reads: [] };

/** The parameter of the address that names the import whose report the screen shows. */
export const IMPORT_PARAMETER = "import";

/** The address of the report of an import, from that of the screen and its context. */
export function importHref(start: string, importId: string): string {
  const [path = "", query = ""] = start.split("?");
  const search = new URLSearchParams(query);
  search.set(IMPORT_PARAMETER, importId);
  return `${path}?${search.toString()}`;
}

/** The path the browser shows now: an answer checks it before it navigates. Browser only. */
export function shownScreen(): string {
  return window.location.pathname;
}

/** The import whose report the browser shows now, if any. Browser only. */
export function shownImport(): string | null {
  return new URLSearchParams(window.location.search).get(IMPORT_PARAMETER);
}
