// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a screen of a project reads in, read on the server once per request however many
 * components ask — the page, the title of its tab, the banner of its context: the project,
 * the revision the address names, the sub-project a filter restricts to. The banner shows it
 * (WF-IHM-0020), and a screen receives it as a prop, whether its revision is read only
 * included, rather than deducing any of it again.
 */
import "server-only";

import { cache } from "react";

import type { components } from "@/api/generated/schema";
import { isGatewayFailure, reach } from "@/api/problem";
import { serverClient } from "@/api/server";
import {
  type ContextParameter,
  type ProjectContext,
  readContext,
  type SearchParameters,
  UNASSIGNED,
} from "@/navigation/context";

import { availableEdits, type EditCommand, isReadOnly, type Revision } from "./read-only";

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
   * The commands of modification of the revision the caller may exercise now: a grid reads
   * its own — `edits.has("edit_planning")` —, never `readOnly`. Empty without a revision.
   */
  readonly edits: ReadonlySet<EditCommand>;
  /**
   * Whether no command of modification of the revision is available — it is marked, or the
   * caller may modify nothing of it: what the notice of the banner says, and nothing more.
   */
  readonly readOnly: boolean;
  /** The active filters, in the order of the parameters of the context. */
  readonly filters: readonly ContextFilter[];
}

/**
 * An answer of the API to a read of a screen that is neither a success nor "not found": a
 * refusal without a session — a screen of a project means nothing without an account — or a
 * failure of the server. The page does not swallow it: it throws, and the screen of failure
 * shows it (US-0090/L2, #101).
 */
export class UnexpectedAnswer extends Error {
  /** The answer of an operation, by its `operationId` and its status. */
  constructor(
    readonly operation: string,
    readonly status: number,
  ) {
    super(`${operation} answered ${String(status)}`);
    this.name = "UnexpectedAnswer";
  }
}

/** Throw on an answer that is neither a success nor "not found"; leave the others be. */
function refuseUnexpected(
  operation: string,
  answer: { readonly response: Response } | undefined,
): void {
  const status = answer?.response.status;
  if (status !== undefined && status !== 404 && !answer?.response.ok) {
    throw new UnexpectedAnswer(operation, status);
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

/** Read the sub-projects of a project, once per request (`listSubprojects`). */
const readSubprojects = cache(async (projectId: string) =>
  readApi(() =>
    serverClient().GET("/projects/{project_id}/subprojects", {
      params: { path: { project_id: projectId } },
    }),
  ),
);

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

/** The filters of a context, with what each restricts. */
async function readFilters(context: ProjectContext): Promise<ContextFilter[]> {
  const subprojectId = context.parameters.get("subproject_id");
  const asOf = context.parameters.get("as_of");
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
 * Read what a screen of a project reads in, and say what the page is to do with it:
 *
 * - `"not_found"` when the API finds neither the project nor the revision the address names
 *   — or does not let the user read them, which it answers alike (WF-ADM-0110): the page is
 *   not found;
 * - `undefined` when the API cannot be reached at all — `fetch` rejected, or a gateway said
 *   the service is down (`isGatewayFailure`): there is nothing to name, so no banner, and the page goes on to say the API is out of reach (US-0090/L2, #101);
 * - the reading itself on success.
 *
 * Any other answer — no session, a failure of the server — throws `UnexpectedAnswer`: a
 * banner left out on such an answer would hide which revision the screen reads in.
 */
export async function readProjectContext(
  pathname: string,
  context: ProjectContext,
): Promise<ProjectReading | "not_found" | undefined> {
  const { projectId, revisionId } = context;
  const [project, revision, filters] = await Promise.all([
    readProject(projectId),
    revisionId === undefined ? undefined : readRevision(projectId, revisionId),
    readFilters(context),
  ]);
  if (project?.response.status === 404 || revision?.response.status === 404) {
    return "not_found";
  }
  refuseUnexpected("getProject", project);
  refuseUnexpected("getRevision", revision);
  if (project?.data === undefined || (revisionId !== undefined && revision?.data === undefined)) {
    return undefined;
  }
  const read = revision?.data;
  return {
    pathname,
    context,
    project: project.data,
    revision: read,
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
): Promise<ProjectReading | "not_found" | undefined> {
  const context = readContext(pathname, search);
  return context === undefined ? "not_found" : readProjectContext(pathname, context);
}
