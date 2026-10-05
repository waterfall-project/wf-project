// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the imports and exports offers, which both its server and its client parts read: the
 * import of each kind of file, as the server offers its command (WF-IHM-0090); what an import
 * still lets the user do, by its status; and the address of the report of an import.
 *
 * The contract names one command of import, that of the actual costs, on the project
 * (`import_actual_costs`). A planning, an estimate, a remaining are imported into the current
 * revision (WF-INTF-0090): their import is offered as the command that modifies the same content
 * of that revision — `edit_planning`, `edit_estimate`, `edit_remaining` —, and not without a
 * current revision, until the contract says it (#318). The front deduces nothing from a
 * permission.
 */
import type { components } from "@/api/generated/schema";
import { type CommandOffer, findOffer } from "@/components/commands/offer";
import type { Project } from "@/components/context/reading";
import type { Revision } from "@/components/context/read-only";
import { OFFSET } from "@/components/grid/query";

type ExchangeKind = components["schemas"]["ExchangeKind"];
type ImportStatus = components["schemas"]["Import"]["status"];
type RevisionCommand = components["schemas"]["RevisionCommand"];

/** The kinds of file an import reads, in the order of the flows (FLX-01 to FLX-07). */
export const EXCHANGE_KINDS: readonly ExchangeKind[] = [
  "ms_project_schedule",
  "estimate",
  "remaining",
  "actual_costs",
];

/** A kind of file an import writes into the current revision. */
type RevisionKind = Exclude<ExchangeKind, "actual_costs">;

/** The command of the current revision that modifies what an import of a kind writes. */
const REVISION_COMMAND: Readonly<Record<RevisionKind, RevisionCommand>> = {
  ms_project_schedule: "edit_planning",
  estimate: "edit_estimate",
  remaining: "edit_remaining",
};

/** The import of each kind, as the server offers it; `undefined` where it is not offered. */
export type ImportOffers = Readonly<Record<ExchangeKind, CommandOffer | undefined>>;

/** What the project and its current revision, when it has one, offer of each import. */
export function importOffers(project: Project, current: Revision | undefined): ImportOffers {
  const ofRevision = (kind: RevisionKind) =>
    current === undefined
      ? undefined
      : findOffer(current.available_commands, REVISION_COMMAND[kind]);
  return {
    ms_project_schedule: ofRevision("ms_project_schedule"),
    estimate: ofRevision("estimate"),
    remaining: ofRevision("remaining"),
    actual_costs: findOffer(project.available_commands, "import_actual_costs"),
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
