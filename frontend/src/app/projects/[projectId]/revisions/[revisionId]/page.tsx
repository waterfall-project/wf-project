// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A revision itself, which is no function of the navigation: the server leads to the first
 * function of a revision the session may read, in the order of the FBS and of the sidebar —
 * the planning (FBS-4.3), then the estimate (FBS-4.4) —, the reading context of the address
 * carried on. The planning comes first as it does in the sidebar and in the mock-up, the tree
 * drawn before it is costed; an estimator who may not read the planning is led to the estimate
 * rather than to a planning the API would refuse him. Without a function to read — no session,
 * or none of a revision —, the planning, whose page leads to the sign-in or is not found.
 */
import { notFound, redirect } from "next/navigation";

import { type PageSearchParams, pageSearch, readContext } from "@/navigation/context";
import { functionOf, type NavigationFunction, readableGroups } from "@/navigation/functions";
import { requestSession } from "@/session/request";

/** The route parameters of a revision. */
export interface RevisionParams {
  readonly projectId: string;
  readonly revisionId: string;
}

/** The query of an address, as Next hands it to a page: a repeated parameter keeps each value. */
function queryOf(search: PageSearchParams): string {
  const query = new URLSearchParams();
  for (const [name, value] of Object.entries(search)) {
    for (const each of typeof value === "string" ? [value] : (value ?? [])) {
      query.append(name, each);
    }
  }
  const text = query.toString();
  return text === "" ? "" : `?${text}`;
}

/**
 * The function a revision leads to: the first function of a revision the session may read, in
 * the order of the FBS; the planning when there is none to read — its page is then not found,
 * or leads to the sign-in without a session.
 */
async function openingFunction(): Promise<NavigationFunction> {
  const session = await requestSession();
  const readable = readableGroups(session?.permissions ?? [])
    .flatMap((group) => group.functions)
    .find((fn) => fn.scope === "revision");
  return readable ?? functionOf("planning");
}

/** Lead from a revision to the first of its functions the session may read. */
export default async function RevisionPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const pathname = `/projects/${revision.projectId}/revisions/${revision.revisionId}`;
  if (readContext(pathname, pageSearch(search)) === undefined) {
    notFound();
  }
  const { route } = await openingFunction();
  redirect(`${pathname}/${route.slice(route.lastIndexOf("/") + 1)}${queryOf(search)}`);
}
