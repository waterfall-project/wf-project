// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The reading context of a project, which the address carries (WF-IHM-0010): the project and
 * the revision in the path, the filtered sub-project and the calculation date as parameters,
 * named as the contract names them. The links between functions carry it on; a cookie of the
 * front keeps the last one, so that a function outside any project leads back to it.
 *
 * Pure: the navigation reads the address, the root layout the cookie; neither keeps a copy
 * of the context elsewhere.
 */

/** The parameters of the address that belong to the context, as the contract names them. */
export const CONTEXT_PARAMETERS = ["subproject_id", "as_of"] as const;

/** The cookie of the front that keeps the address of the last project context. */
export const LAST_CONTEXT_COOKIE = "wf_last_project";

// A year: the context of a project outlives a session, as a bookmark would.
const COOKIE_AGE = 60 * 60 * 24 * 365;

// A project, a revision of it, and the function read in it: /projects/P/revisions/R/f.
const PROJECT_PATH = /^\/projects\/([^/?#]+)(?:\/revisions\/([^/?#]+))?(?:\/[^?#]*)?$/;

/** What a screen of a project reads in: its project and revision, and its filters. */
export interface ProjectContext {
  readonly projectId: string;
  readonly revisionId: string | undefined;
  /** The parameters of the context the address gives, in the order of CONTEXT_PARAMETERS. */
  readonly parameters: URLSearchParams;
}

/** What the navigation reads of the address: its search parameters. */
export interface SearchParameters {
  get(name: string): string | null;
}

/**
 * The context of the project an address reads in, or `undefined` outside any project — the
 * list of projects included.
 */
export function readContext(
  pathname: string,
  search: SearchParameters,
): ProjectContext | undefined {
  const match = PROJECT_PATH.exec(pathname);
  const projectId = match?.[1];
  if (projectId === undefined) {
    return undefined;
  }
  const parameters = new URLSearchParams();
  for (const name of CONTEXT_PARAMETERS) {
    const value = search.get(name);
    if (value !== null && value !== "") {
      parameters.set(name, value);
    }
  }
  return { projectId, revisionId: match?.[2], parameters };
}

/** The search part of an address that carries the parameters of a context, or nothing. */
export function contextQuery(context: ProjectContext): string {
  const query = context.parameters.toString();
  return query === "" ? "" : `?${query}`;
}

/**
 * The address of the last project context, read from the cookie: `undefined` when there is
 * none, or when the value is not the address of a project — a cookie is the browser's to
 * change, and the shell only ever leads back into a project.
 */
export function rememberedAddress(value: string | undefined): string | undefined {
  if (value === undefined) {
    return undefined;
  }
  const [pathname = "", query = ""] = value.split("?", 2);
  const context = readContext(pathname, new URLSearchParams(query));
  return context === undefined ? undefined : pathname + contextQuery(context);
}

/** The cookie that keeps the address of a project context, for `document.cookie`. */
export function contextCookie(address: string): string {
  const value = encodeURIComponent(address);
  return `${LAST_CONTEXT_COOKIE}=${value}; path=/; max-age=${String(COOKIE_AGE)}; samesite=lax`;
}
