// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The reading context of a project, which the address carries (WF-IHM-0010): the project in
 * the path; the revision in the path too for the functions that read in it, and as the
 * parameter `revision_id` for the functions of the project itself, which a project without a
 * revision keeps; the filtered sub-project and the calculation date as parameters — all named
 * as the contract names them. The links between functions carry it on; a cookie of the front
 * keeps the last one, so that a function outside any project leads back to it.
 *
 * Pure: the navigation reads the address, the root layout the cookie; neither keeps a copy
 * of the context elsewhere.
 */
import { EXCHANGES_SCREEN } from "./exchanges";
import table from "./functions.json";

/** The parameters of the address that filter what a screen reads, as the contract names them. */
export const CONTEXT_PARAMETERS = ["subproject_id", "as_of"] as const;

/** The value of `subproject_id` that restricts to what belongs to no sub-project (WF-IND-0020). */
export const UNASSIGNED = "unassigned";

/** The parameter that carries the revision on a screen of the project itself. */
export const REVISION_PARAMETER = "revision_id";

/** The cookie of the front that keeps the address of the last project context. */
export const LAST_CONTEXT_COOKIE = "wf_last_project";

// A year: the context of a project outlives a session, as a bookmark would.
const COOKIE_AGE = 60 * 60 * 24 * 365;

// An identifier in a path, as the contract makes them: never `.`, `..`, empty, nor encoded.
const IDENTIFIER = /^[\w-]+$/;

/** A function of the table, as this module reads it: its scope, its route, its leaves. */
interface Routed {
  readonly scope: string;
  readonly route: string;
  readonly leaves?: readonly Routed[];
}

/**
 * The last segment of the routes of the functions of a scope, and of their leaves with a screen
 * of their own: `lifecycle`, `planning`, `workload`…
 */
function screens(scope: string): ReadonlySet<string> {
  const functions: readonly Routed[] = table.groups.flatMap((group) => group.functions);
  const routes = functions
    .flatMap((fn) => [fn, ...(fn.leaves ?? [])])
    .filter((fn) => fn.scope === scope)
    .map((fn) => fn.route);
  return new Set(routes.map((route) => route.slice(route.lastIndexOf("/") + 1)));
}

// The screens of the project itself: its functions, and the exchanges by file.
const PROJECT_SCREENS = new Set([...screens("project"), EXCHANGES_SCREEN]);
const REVISION_SCREENS = screens("revision");

/** What a screen of a project reads in: its project and revision, and its filters. */
export interface ProjectContext {
  readonly projectId: string;
  readonly revisionId: string | undefined;
  /** Whether the path names the revision, or the parameter `revision_id` carries it. */
  readonly revisionInPath: boolean;
  /** The filters the address gives, in the order of CONTEXT_PARAMETERS. */
  readonly parameters: URLSearchParams;
}

/** What the navigation reads of the address: its search parameters. */
export interface SearchParameters {
  get(name: string): string | null;
}

/**
 * The revision the rest of a path names after its project — `undefined` for none —, or
 * nothing when the path is no screen of a project: the project alone, a function of the
 * project, a revision, a function of a revision.
 */
function followProject(tail: readonly string[]): { revisionId: string | undefined } | undefined {
  const [first, second, third, ...more] = tail;
  if (first === undefined) {
    return { revisionId: undefined };
  }
  if (second === undefined) {
    return PROJECT_SCREENS.has(first) ? { revisionId: undefined } : undefined;
  }
  if (first !== "revisions" || !IDENTIFIER.test(second) || more.length > 0) {
    return undefined;
  }
  return third === undefined || REVISION_SCREENS.has(third) ? { revisionId: second } : undefined;
}

/** A parameter of the address, when it has a value. */
function parameter(search: SearchParameters, name: string): string | undefined {
  const value = search.get(name);
  return value === null || value === "" ? undefined : value;
}

/**
 * The context of the project an address reads in, or `undefined` outside any project — the
 * list of projects included — or on an address that is no screen of a project.
 */
export function readContext(
  pathname: string,
  search: SearchParameters,
): ProjectContext | undefined {
  const [root, projectId = "", ...tail] = pathname.split("/").slice(1);
  const followed =
    root === "projects" && IDENTIFIER.test(projectId) ? followProject(tail) : undefined;
  if (followed === undefined) {
    return undefined;
  }
  const parameters = new URLSearchParams();
  for (const name of CONTEXT_PARAMETERS) {
    const value = parameter(search, name);
    if (value !== undefined) {
      parameters.set(name, value);
    }
  }
  const carried = parameter(search, REVISION_PARAMETER);
  return {
    projectId,
    revisionId:
      followed.revisionId ??
      (carried !== undefined && IDENTIFIER.test(carried) ? carried : undefined),
    revisionInPath: followed.revisionId !== undefined,
    parameters,
  };
}

/**
 * The search part of an address that carries a context, or nothing: the revision first when
 * the path does not name it, then the filters.
 */
export function contextQuery(context: ProjectContext, carryRevision: boolean): string {
  const query = new URLSearchParams();
  if (carryRevision && context.revisionId !== undefined) {
    query.set(REVISION_PARAMETER, context.revisionId);
  }
  for (const [name, value] of context.parameters) {
    query.set(name, value);
  }
  const text = query.toString();
  return text === "" ? "" : `?${text}`;
}

/** The address of the screen a context was read on: its path, and the context it carries. */
export function contextAddress(pathname: string, context: ProjectContext): string {
  return pathname + contextQuery(context, !context.revisionInPath);
}

/** A filter the address of a context may carry: `subproject_id` or `as_of`. */
export type ContextParameter = (typeof CONTEXT_PARAMETERS)[number];

/**
 * The address of the same screen with one filter lifted: the revision and the other filter
 * kept, as a link that removes it from the address.
 */
export function withoutFilter(
  pathname: string,
  context: ProjectContext,
  name: ContextParameter,
): string {
  const parameters = new URLSearchParams(context.parameters);
  parameters.delete(name);
  return contextAddress(pathname, { ...context, parameters });
}

/** The search parameters of a page, as Next hands them to it: a repeated one counts once. */
export type PageSearchParams = Readonly<Record<string, string | readonly string[] | undefined>>;

/** Read the search parameters of a page as the navigation reads those of the browser. */
export function pageSearch(search: PageSearchParams): SearchParameters {
  return {
    get(name) {
      const value = Object.hasOwn(search, name) ? search[name] : undefined;
      const first = typeof value === "string" ? value : value?.[0];
      return first ?? null;
    },
  };
}

/**
 * The address of the last project context, read from the cookie: `undefined` when there is
 * none, or when the value is not the address of a screen of a project — a cookie is the
 * browser's to change, and the shell only ever leads back into a project.
 */
export function rememberedAddress(value: string | undefined): string | undefined {
  if (value === undefined) {
    return undefined;
  }
  const [pathname = "", query = ""] = value.split("?", 2);
  const context = readContext(pathname, new URLSearchParams(query));
  return context === undefined ? undefined : contextAddress(pathname, context);
}

/** The cookie that keeps the address of a project context, for `document.cookie`. */
export function contextCookie(address: string): string {
  const value = encodeURIComponent(address);
  return `${LAST_CONTEXT_COOKIE}=${value}; path=/; max-age=${String(COOKIE_AGE)}; samesite=lax`;
}

/**
 * The cookie that forgets the last project context, for `document.cookie`: it is no account's,
 * and signing out leaves nothing of it to the next user of the workstation.
 */
export function forgottenContextCookie(): string {
  return `${LAST_CONTEXT_COOKIE}=; path=/; max-age=0; samesite=lax`;
}
