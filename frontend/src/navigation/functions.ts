// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The functions of the FBS the navigation offers, read from `functions.json`: for each
 * function of the second level, its code, the key of its label in the catalogues, its route,
 * whether it lives outside any project or in one, and the permission that lets a user read
 * it (WF-ADM-0100). The navigation is drawn from this table, and so is the page that stands
 * for a screen still to come.
 *
 * The table is data: functions.test.ts checks it against the catalogues and the FBS.
 */
import type { components } from "@/api/generated/schema";
import type { Catalogue } from "@/i18n/catalogues";

import { contextQuery, type ProjectContext } from "./context";
import table from "./functions.json";

type PermissionCode = components["schemas"]["PermissionCode"];
type Readable<P> = P extends `${infer F}.read` ? F : never;

/**
 * The name of a function in the catalogue of permissions: `planning` stands for
 * `planning.read` and `planning.write`.
 */
export type FunctionPermission = Readable<PermissionCode>;

/** Where a function lives: outside any project, or in the revision of one. */
export type Scope = "platform" | "project";

/** A function of the second level of the FBS, as the navigation offers it. */
export interface NavigationFunction {
  readonly code: string;
  readonly label: `functions.${keyof Catalogue["functions"]}`;
  /**
   * Its route; a function of a project names the segments of its context:
   * `/projects/[projectId]/revisions/[revisionId]/planning`.
   */
  readonly route: string;
  readonly scope: Scope;
  readonly permission: FunctionPermission;
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
 * The address of a function: its route outside a project; in a project, its route in the
 * context given — the same revision, sub-project and calculation date. `undefined` for a
 * function of a project without a revision to read in.
 */
export function functionHref(
  fn: NavigationFunction,
  context: ProjectContext | undefined,
): string | undefined {
  if (fn.scope === "platform") {
    return fn.route;
  }
  if (context?.revisionId === undefined) {
    return undefined;
  }
  const path = fn.route
    .replace(CONTEXT_SEGMENTS.projectId, context.projectId)
    .replace(CONTEXT_SEGMENTS.revisionId, context.revisionId);
  return path + contextQuery(context);
}

/** A function an address leads to, and the project it reads in, if any. */
export interface Screen {
  readonly fn: NavigationFunction;
  readonly projectId: string | undefined;
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
  for (const group of FUNCTION_GROUPS) {
    for (const fn of group.functions) {
      const route = fn.route.split("/").slice(1);
      if (follows(route, segments)) {
        const at = route.indexOf(CONTEXT_SEGMENTS.projectId);
        return { fn, projectId: at === -1 ? undefined : segments[at] };
      }
    }
  }
  return undefined;
}
