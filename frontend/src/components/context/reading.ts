// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a screen of a project reads in, read on the server once per request however many
 * components ask — the page, the title of its tab, the banner of its context: the project,
 * the revision the address names, the sub-project a filter restricts to. The banner shows it
 * (WF-IHM-0020), and a screen receives it as a prop, whether its revision is read only
 * included, rather than deducing any of it again.
 *
 * A screen declares the parameters of the context its reads take (`reads`), and the banner shows
 * those filters alone (#302): the address carries `as_of` and `subproject_id` on to every screen
 * of the project, but a workload, a lifecycle, a list of imports read neither, and a chip would say
 * a figure filtered or dated that is not.
 *
 * A screen that reads in a revision reads the revisions of its project too, every page of them
 * (`listRevisions`), which the banner offers to read instead (US-2330): once per request, beside the
 * project and the revision, and shared with the screens that list them (`readRevisions`).
 */
import "server-only";

import { cache } from "react";

import { Unreachable } from "@/api/client";
import { readEveryPageUnlessRefused } from "@/api/every-page";
import type { components } from "@/api/generated/schema";
import { type ExpectedRefusal, isGatewayFailure, reach, refusalOf } from "@/api/problem";
import { serverClient } from "@/api/server";
import {
  type ContextParameter,
  type ProjectContext,
  readContext,
  type SearchParameters,
  UNASSIGNED,
} from "@/navigation/context";

import { startReading } from "@/components/start-reading";

import { availableEdits, type EditCommand, isReadOnly, type Revision } from "./read-only";
import { type ListedRevision, listedRevision } from "./revision";

/** A project, as the API reads it. */
export type Project = components["schemas"]["Project"];

/** A sub-project of a project, which a filter may restrict a screen to. */
export type Subproject = components["schemas"]["Subproject"];

/**
 * A filter the address holds, with what it restricts: the sub-project a `subproject_id`
 * names — `undefined` for `unassigned`, or for one the project does not have —, the date of
 * an `as_of`.
 */
export type ContextFilter =
  | {
      readonly name: Extract<ContextParameter, "subproject_id">;
      readonly value: string;
      readonly subproject: Subproject | undefined;
    }
  | { readonly name: Extract<ContextParameter, "as_of">; readonly value: string };

/** What a screen of a project reads in, and what the banner of its context shows. */
export interface ProjectReading {
  /** The path of the screen, which the links that lift a filter keep. */
  readonly pathname: string;
  readonly context: ProjectContext;
  readonly project: Project;
  /** The revision the screen reads in; none on a function of the project without one. */
  readonly revision: Revision | undefined;
  /**
   * The revisions of the project, as the server lists them — the most recent first —, which the
   * banner offers to read instead of the revision read; none without a revision.
   */
  readonly revisions?: readonly ListedRevision[] | undefined;
  /**
   * The commands of modification of the revision the caller may exercise now. A grid does not
   * read its entry from them but from the main structure it reads (`GridScreen.commands`), never
   * from `readOnly` either. Empty without a revision.
   */
  readonly edits: ReadonlySet<EditCommand>;
  /**
   * Whether no command of modification of the revision is available — it is marked, or the
   * caller may modify nothing of it: what the notice of the banner says, and nothing more.
   */
  readonly readOnly: boolean;
  /**
   * The active filters among those the screen reads, in the order of the parameters of the
   * context.
   */
  readonly filters: readonly ContextFilter[];
}

/** Throw on an answer that is neither a success nor "not found"; leave the others be. */
function refuseUnexpected(
  operation: string,
  answer: { readonly response: Response; readonly error?: unknown } | undefined,
): void {
  const status = answer?.response.status;
  if (status !== undefined && status !== 404 && !answer?.response.ok) {
    throw refusalOf(operation, status, answer?.error);
  }
}

/**
 * Call the API for a read, or `undefined` when it is out of reach: `fetch` rejected, or a
 * gateway answered that the service behind it is down — the verdict `decode` gives an action.
 */
async function readApi<A extends { readonly response: Response; readonly error?: unknown }>(
  call: () => Promise<A>,
): Promise<A | undefined> {
  const answer = await reach(call);
  return answer === undefined || isGatewayFailure(answer.response, answer.error)
    ? undefined
    : answer;
}

/** Read a project, once per request (`getProject`); `undefined` when the API is out of reach. */
export const readProject = cache(async (projectId: string) =>
  readApi(() =>
    serverClient().GET("/projects/{project_id}", {
      params: { path: { project_id: projectId } },
    }),
  ),
);

/** Read a revision of a project, once per request (`getRevision`). */
export const readRevision = cache(async (projectId: string, revisionId: string) =>
  readApi(() =>
    serverClient().GET("/projects/{project_id}/revisions/{revision_id}", {
      params: { path: { project_id: projectId, revision_id: revisionId } },
    }),
  ),
);

/** The refusal of the revisions of a project the contract declares: not found, or not readable. */
const REVISIONS_REFUSED = [{ status: 404 }] as const satisfies readonly ExpectedRefusal[];

/**
 * Read every revision of a project, once per request (`listRevisions`, every page), or `undefined`
 * when the API refuses them (404): the banner offers them, and does without them — a session that may
 * read a revision and not their list keeps its screen, without the choice —; the screens that list
 * them — the page of the project, the revisions — read the same answer, and are not found without
 * it.
 */
export const readRevisions = cache((projectId: string) =>
  readEveryPageUnlessRefused("listRevisions", REVISIONS_REFUSED, (page) =>
    serverClient().GET("/projects/{project_id}/revisions", {
      params: { path: { project_id: projectId }, query: page },
    }),
  ),
);

/**
 * Ask the sub-projects of a project, once per request (`listSubprojects`): the banner names the
 * one a filter restricts to, and a screen that filters on them offers them — each reading the one
 * answer by its own rule.
 */
export const askSubprojects = cache((projectId: string) =>
  serverClient().GET("/projects/{project_id}/subprojects", {
    params: { path: { project_id: projectId } },
  }),
);

/** Read the sub-projects of a project, or nothing when the API is out of reach. */
function readSubprojects(projectId: string) {
  return readApi(() => askSubprojects(projectId));
}

/** The sub-project a filter names, read only when it names one rather than `unassigned`. */
async function filteredSubproject(
  projectId: string,
  value: string,
): Promise<Subproject | undefined> {
  if (value === UNASSIGNED) {
    return undefined;
  }
  const answer = await readSubprojects(projectId);
  refuseUnexpected("listSubprojects", answer);
  return answer?.data?.find((subproject) => subproject.subproject_id === value);
}

/** The filters of a context the screen reads, with what each restricts. */
async function readFilters(
  context: ProjectContext,
  reads: readonly ContextParameter[],
): Promise<ContextFilter[]> {
  const read = (name: ContextParameter) =>
    reads.includes(name) ? context.parameters.get(name) : null;
  const subprojectId = read("subproject_id");
  const asOf = read("as_of");
  const subproject =
    subprojectId === null ? undefined : await filteredSubproject(context.projectId, subprojectId);
  return [
    ...(subprojectId === null
      ? []
      : [{ name: "subproject_id" as const, value: subprojectId, subproject }]),
    ...(asOf === null ? [] : [{ name: "as_of" as const, value: asOf }]),
  ];
}

/**
 * Start reading the revisions the banner offers, when the screen reads in a revision; none else. The
 * read goes beside the others, and is awaited only once they found the project and the revision: a
 * project not found is not found, whatever its revisions answered.
 */
function startRevisions(
  projectId: string,
  revisionId: string | undefined,
): Promise<readonly ListedRevision[] | undefined> {
  return revisionId === undefined
    ? Promise.resolve(undefined)
    : startReading(readRevisions(projectId).then((all) => all?.map(listedRevision)));
}

/**
 * Read what a screen of a project reads in — `reads` naming the parameters of the context its
 * reads take, whose filters alone the banner shows —, and say what the page is to do with it:
 *
 * - `"not_found"` when the API finds neither the project nor the revision the address names
 *   — or does not let the user read them, which it answers alike (WF-ADM-0110): the page is
 *   not found;
 * - the reading itself on success.
 *
 * The API out of reach — `fetch` rejected, or a gateway said the service is down
 * (`isGatewayFailure`) — throws `Unreachable`, which the screen of failure announces as such;
 * a 401 throws `SignedOut`, which leads to the sign-in page; a 503 that names a component of
 * the platform throws `ComponentUnavailable`; any other answer — a failure of the server —
 * throws `UnexpectedAnswer`: a screen of a project left without its banner would
 * hide which revision it reads in.
 */
export async function readProjectContext(
  pathname: string,
  context: ProjectContext,
  reads: readonly ContextParameter[],
): Promise<ProjectReading | "not_found"> {
  const { projectId, revisionId } = context;
  const listed = startRevisions(projectId, revisionId);
  const [project, revision, filters] = await Promise.all([
    readProject(projectId),
    revisionId === undefined ? undefined : readRevision(projectId, revisionId),
    readFilters(context, reads),
  ]);
  if (project?.response.status === 404 || revision?.response.status === 404) {
    return "not_found";
  }
  refuseUnexpected("getProject", project);
  refuseUnexpected("getRevision", revision);
  // What is left without its data is out of reach: every other answer was refused above.
  if (project?.data === undefined || (revisionId !== undefined && revision?.data === undefined)) {
    throw new Unreachable();
  }
  const read = revision?.data;
  const revisions = await listed;
  return {
    pathname,
    context,
    project: project.data,
    revision: read,
    revisions,
    edits: read === undefined ? new Set() : availableEdits(read),
    readOnly: read !== undefined && isReadOnly(read),
    filters,
  };
}

/**
 * Read what the screen at an address reads in, as `readProjectContext` does; `"not_found"`
 * too when the address is no screen of a project — its project or revision named by what is
 * no identifier of the contract.
 */
export async function readAddress(
  pathname: string,
  search: SearchParameters,
  reads: readonly ContextParameter[],
): Promise<ProjectReading | "not_found"> {
  const context = readContext(pathname, search);
  return context === undefined ? "not_found" : readProjectContext(pathname, context, reads);
}
