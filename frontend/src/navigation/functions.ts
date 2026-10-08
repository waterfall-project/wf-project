// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The functions of the FBS the navigation offers, read from `functions.json`: for each
 * function of the second level, its code, the key of its label in the catalogues, its route,
 * whether it lives outside any project or in one, and the permission that lets a user read
 * it (WF-ADM-0100). The navigation is drawn from this table. A leaf of the FBS with a screen of its own — the workload of the
 * project, FBS-4.4.4 — is a leaf of its function in the table: of the same scope and permission,
 * reached from the screen of its function rather than from the navigation, and read in its
 * context as its function is. A leaf the screen of its function shows itself — the calendars on the
 * settings of the resources, FBS-3.2.3 — is a section of its function: addressed by its route, and
 * found on its screen by its role and its name, or by its text in the named list of its facts.
 *
 * The table is data: functions.test.ts checks it against the catalogues, `make screens` against
 * the FBS of the specification and the pages of the application, and `e2e/screens.spec.ts` reaches
 * each of its routes from a link.
 */
import type { components } from "@/api/generated/schema";
import type { Catalogue } from "@/i18n/catalogues";

import { contextQuery, type ProjectContext } from "./context";
import table from "./functions.json";

type PermissionCode = components["schemas"]["PermissionCode"];
type Readable<P> = P extends `${infer F}.read` ? F : never;
type Writable<P> = P extends `${infer F}.write` ? F : never;

/**
 * The name of a function in the catalogue of permissions: `planning` stands for
 * `planning.read` and `planning.write`. The consultation of the journal of audit, which has no
 * permission to modify (`audit_log.read`, WF-SEC-0030), is no such function until the FBS gives
 * it one and the navigation a screen (#518, #517).
 */
export type FunctionPermission = Readable<PermissionCode> & Writable<PermissionCode>;

/**
 * The functions outside any project, by the name of their permissions: those whose commands
 * follow the permission of modification of the session rather than the `available_commands`
 * of an object (WF-ADM-0100). `functions.test.ts` checks the list against the table.
 */
export const PLATFORM_FUNCTIONS = [
  "users",
  "access_roles",
  "system_status",
  "backups",
  "portfolio_projects",
  "portfolio_workload",
  "portfolio_performance",
  "portfolio_cost_structure",
  "portfolio_risks",
  "portfolio_cost_curve",
  "portfolio_pilot_health",
  "cost_settings",
  "resource_settings",
  "risk_settings",
  "indicator_settings",
] as const satisfies readonly FunctionPermission[];

/** A function outside any project, by the name of its permissions. */
export type PlatformFunction = (typeof PLATFORM_FUNCTIONS)[number];

/**
 * Where a function lives: outside any project; in a project, for the functions of the
 * project itself — its revisions, its settings, its lifecycle —, which a project without a
 * revision has; in a revision of a project, for the functions that read one.
 */
export type Scope = "platform" | "project" | "revision";

/** The roles of what shows a section of a screen, as a browser exposes them. */
export type SectionRole = "region" | "grid" | "treegrid" | "columnheader" | "heading";

/**
 * A leaf of the FBS the screen of its function shows itself — a section, a grid, a column, a
 * card, a fact —, where the ergonomics gathered it: addressed by the route of its function.
 */
export interface ScreenSection {
  readonly code: string;
  /**
   * The role of what shows it on the screen, found by it and its name; none for a fact of a list,
   * a term, which takes no name from what it says, and is found by its text in its list.
   */
  readonly role?: SectionRole;
  /** The key, in the catalogues, of the name of the list a fact is found in, which names it. */
  readonly within?: string;
  /** The key, in the catalogues, of its name on the screen: the title of a section, a card. */
  readonly name: string;
}

/** A function of the second level of the FBS, as the navigation offers it. */
export interface NavigationFunction {
  readonly code: string;
  readonly label: `functions.${keyof Catalogue["functions"]}`;
  /**
   * Its route; a function of a project names the segments of its context:
   * `/projects/[projectId]/lifecycle`, `/projects/[projectId]/revisions/[revisionId]/planning`.
   */
  readonly route: string;
  readonly scope: Scope;
  readonly permission: FunctionPermission;
  /** Its leaves that its screen shows itself. */
  readonly sections?: readonly ScreenSection[];
  /** Its leaves that have a screen of their own, which its screen leads to. */
  readonly leaves?: readonly NavigationFunction[];
}

/** A function of the first level of the FBS, and its functions. */
export interface FunctionGroup {
  readonly code: string;
  readonly label: `functionGroups.${keyof Catalogue["functionGroups"]}`;
  /** The page of the group itself, when it has one: the list of projects. */
  readonly route?: string;
  readonly functions: readonly NavigationFunction[];
}

/** The functions of the FBS, by group, in the order of the FBS. */
export const FUNCTION_GROUPS = table.groups as readonly FunctionGroup[];

/** The segments of a route that stand for the context of a project. */
const CONTEXT_SEGMENTS = { projectId: "[projectId]", revisionId: "[revisionId]" } as const;

/**
 * The groups and functions a user may read: a function whose read permission the session
 * lacks is not offered, and a group left without a function nor a page of its own neither.
 */
export function readableGroups(permissions: readonly PermissionCode[]): FunctionGroup[] {
  const granted = new Set<string>(permissions);
  return FUNCTION_GROUPS.map((group) => ({
    ...group,
    functions: group.functions.filter((fn) => granted.has(`${fn.permission}.read`)),
  })).filter((group) => group.route !== undefined || group.functions.length > 0);
}

/**
 * The functions offered when the session cannot be read — the API out of reach, or an answer
 * that is neither a session nor its absence: the status screen alone, which must stay
 * reachable when nothing else works (WF-ADM-0130). What it can show then is its own affair.
 */
export function diagnosticGroups(): FunctionGroup[] {
  return FUNCTION_GROUPS.map((group) => ({
    ...group,
    functions: group.functions.filter((fn) => fn.permission === "system_status"),
  })).filter((group) => group.functions.length > 0);
}

/** The functions of the table, those of the second level of the FBS. */
function functions(): readonly NavigationFunction[] {
  return FUNCTION_GROUPS.flatMap((group) => group.functions);
}

/**
 * What the table has not where the front asked for something: a defect of the table or of the
 * code, never of the data — `functions.test.ts` holds the table against the catalogues and the FBS.
 *
 * One convention for searching the table (#317): each `…Of` finds a function the code names and
 * throws through here when the table has none, a miss being a defect; `functionAt` alone gives
 * `undefined`, for a code that comes from the data (`Permission.fbs_code`).
 */
function missing(what: string): never {
  throw new Error(`the table of functions has no ${what}`);
}

/** The function of the table whose permissions bear a name — `planning`, `cost_settings`. */
export function functionOf(permission: FunctionPermission): NavigationFunction {
  return (
    functions().find((fn) => fn.permission === permission) ??
    missing(`function reading with ${permission}.read`)
  );
}

/**
 * A leaf of the table, by its code of the FBS — `FBS-4.3.4` —: a function the navigation does not
 * offer, reached from the screen of its function.
 */
export function leafOf(code: string): NavigationFunction {
  return (
    functions()
      .flatMap((fn) => fn.leaves ?? [])
      .find((leaf) => leaf.code === code) ?? missing(`leaf ${code}`)
  );
}

/**
 * The function of the table of a code of the FBS — `FBS-1.1` —, as a permission of the catalogue
 * names the function it covers (`Permission.fbs_code`); `undefined` for a code the table has not.
 * Only the functions of the second level are searched, as permissions cover them: a leaf of the
 * FBS — `FBS-4.3.2`, a section of the planning — is not found, nor is a block of the first level.
 */
export function functionAt(code: string): NavigationFunction | undefined {
  return functions().find((fn) => fn.code === code);
}

/**
 * The address of a function: its route outside a project; in a project, its route in the
 * context given — the same revision, sub-project and calculation date, the revision as the
 * parameter `revision_id` on a function of the project itself, so that the next function of
 * a revision finds it. `undefined` for a function of a project outside any project, and for
 * a function of a revision without a revision to read in.
 */
export function functionHref(
  fn: NavigationFunction,
  context: ProjectContext | undefined,
): string | undefined {
  if (fn.scope === "platform") {
    return fn.route;
  }
  if (context === undefined) {
    return undefined;
  }
  // A function as replacement: an identifier is inserted as it is, `$&` included.
  const inProject = fn.route.replace(CONTEXT_SEGMENTS.projectId, () => context.projectId);
  if (fn.scope === "project") {
    return inProject + contextQuery(context, true);
  }
  const { revisionId } = context;
  if (revisionId === undefined) {
    return undefined;
  }
  return (
    inProject.replace(CONTEXT_SEGMENTS.revisionId, () => revisionId) + contextQuery(context, false)
  );
}

/**
 * A function an address leads to, the function it is a leaf of if it is one, and the project and
 * the revision it reads in, if any.
 */
export interface Screen {
  readonly fn: NavigationFunction;
  readonly parent: NavigationFunction | undefined;
  readonly projectId: string | undefined;
  readonly revisionId: string | undefined;
}

/** Whether the segments of an address follow those of a route, context segments aside. */
function follows(route: readonly string[], segments: readonly string[]): boolean {
  return (
    route.length === segments.length &&
    route.every(
      (part, index) =>
        part === CONTEXT_SEGMENTS.projectId ||
        part === CONTEXT_SEGMENTS.revisionId ||
        part === segments[index],
    )
  );
}

/** The function the segments of an address lead to, or `undefined` when none does. */
export function findScreen(segments: readonly string[]): Screen | undefined {
  const screens = functions().flatMap((fn) => [
    { fn, parent: undefined },
    ...(fn.leaves ?? []).map((leaf) => ({ fn: leaf, parent: fn })),
  ]);
  for (const { fn, parent } of screens) {
    const route = fn.route.split("/").slice(1);
    if (follows(route, segments)) {
      const segment = (name: string) => {
        const at = route.indexOf(name);
        return at === -1 ? undefined : segments[at];
      };
      return {
        fn,
        parent,
        projectId: segment(CONTEXT_SEGMENTS.projectId),
        revisionId: segment(CONTEXT_SEGMENTS.revisionId),
      };
    }
  }
  return undefined;
}
