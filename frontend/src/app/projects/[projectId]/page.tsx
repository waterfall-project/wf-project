// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A project (US-0210, US-0720), second step of the witness path (US-0080). Once the project has a
 * revision, its screen is a way: the server leads to the revision the user works on — the one in
 * progress, else the reference, else the last one marked —, the reading context of the address and
 * its filters carried on (WF-IHM-0010); to the revisions, when that revision cannot be read by the
 * session, or when the project has revisions but none of those (the import the address names, if
 * any, carried on). A report of an import the address names (`import`) follows to the screen of
 * the exchanges of that revision, which shows it — unless it is the import that creates the first
 * revision, which stays here.
 *
 * A project without a revision keeps its screen: the banner of its reading context (WF-IHM-0020),
 * its label, what it is — its code, its state, its order, its description —, the start of its
 * planning and the imports the project offers: an import creates the revision it applies to
 * (WF-INTF-0090, #332), its report shown above them, applied or abandoned there. A project the API
 * does not find is not found, as at the other screens of a project. Nothing is offered to modify
 * it: its form belongs to the epic of its domain.
 */
import { FolderOpen } from "lucide-react";
import type { Metadata } from "next";
import { redirect } from "next/navigation";

import { readEveryPage } from "@/api/every-page";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { readRevision } from "@/components/context/reading";
import { ImportPart } from "@/components/exchanges/import-part";
import { readMappingGap } from "@/components/exchanges/mapping-gap";
import { ImportReport } from "@/components/exchanges/import-report";
import { IMPORT_PARAMETER, importOffers } from "@/components/exchanges/offers";
import { readShownImport } from "@/components/exchanges/shown-import";
import { createsFirstRevision, openedRevision } from "@/components/projects/opened-revision";
import { ProjectFacts } from "@/components/projects/project-facts";
import { ProjectStart } from "@/components/projects/project-start";
import { startOffers } from "@/components/projects/start-offers";
import { PageHeader, Screen } from "@/components/shell/page-header";
import {
  contextAddress,
  contextQuery,
  pageSearch,
  type ProjectContext,
} from "@/navigation/context";
import { functionHref, functionOf } from "@/navigation/functions";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../title";
import {
  type ProjectPageProps,
  type ProjectParams,
  projectAddress,
  readProjectScreen,
} from "./screen";

/** Title the tab with the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<ProjectParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functionGroups.projects", projectId);
}

/**
 * Lead from the screen of a project to its revision, or to the revisions when the session may not
 * read it, the filters of the address kept; the report of an import the address names goes to the
 * exchanges of the revision, unless the import is the one that creates the first. Returns only
 * for that import: the screen stays.
 */
async function leadTo(
  revisionId: string,
  context: ProjectContext,
  shown: Awaited<ReturnType<typeof readShownImport>>,
): Promise<void> {
  const projectPath = `/projects/${context.projectId}`;
  const answer = await readRevision(context.projectId, revisionId);
  // A read the session may not make answers 404 (WF-ADM-0110): the contract lists no 403.
  if (answer?.response.status === 404) {
    redirect(withImport(`${projectPath}/revisions${contextQuery(context, false)}`, shown));
  }
  const inRevision = { ...context, revisionId, revisionInPath: true };
  if (shown === undefined) {
    redirect(contextAddress(`${projectPath}/revisions/${revisionId}`, inRevision));
  }
  if (!createsFirstRevision(shown)) {
    const exchanges = contextAddress(
      `${projectPath}/revisions/${revisionId}/exchanges`,
      inRevision,
    );
    redirect(withImport(exchanges, shown));
  }
}

/** The address, the report of the import the address names carried on, if it names one. */
function withImport(address: string, shown: Awaited<ReturnType<typeof readShownImport>>): string {
  if (shown === undefined) {
    return address;
  }
  const separator = address.includes("?") ? "&" : "?";
  return `${address}${separator}${IMPORT_PARAMETER}=${encodeURIComponent(shown.import_id)}`;
}

/** Render a project without a revision, what it is and what starts it; lead to a revision else. */
export default async function ProjectPage(props: ProjectPageProps) {
  const [address, search] = await Promise.all([projectAddress(props), props.searchParams]);
  const [revisions, read, session, shown] = await Promise.all([
    readEveryPage("listRevisions", (page) =>
      serverClient().GET("/projects/{project_id}/revisions", {
        params: { path: { project_id: address.projectId }, query: page },
      }),
    ),
    readProjectScreen(address),
    requestSession(),
    readShownImport(address.projectId, pageSearch(search)),
  ]);
  const opened = openedRevision(read.project, revisions);
  if (opened !== undefined) {
    await leadTo(opened, read.context, shown);
  } else if (revisions.length > 0) {
    // Revisions, but none in progress, of reference or marked: the way is their list.
    redirect(
      withImport(contextAddress(`/projects/${address.projectId}/revisions`, read.context), shown),
    );
  }
  const offers = importOffers(read.project);
  // Only a project without a revision shows its imports here.
  const gap =
    revisions.length === 0 ? await readMappingGap(offers, session?.permissions) : undefined;
  // The address of the screen without a report, its context kept.
  const start = contextAddress(address.pathname, read.context);
  // The start of the planning: read at the server, from the revision in progress, which the list
  // of the revisions carries whole (WF-PRJ-0030).
  const current = read.project.current_revision_id ?? undefined;
  const startable = startOffers(
    read.project,
    revisions.find((listed) => listed.revision_id === read.project.current_revision_id),
  );
  const breakdown = functionHref(functionOf("project_settings"), read.context);
  const planning =
    current === undefined
      ? undefined
      : functionHref(functionOf("planning"), {
          ...read.context,
          revisionId: current,
          revisionInPath: true,
        });
  return (
    <>
      <ContextBanner reading={read} />
      <Screen>
        <PageHeader title={read.project.label} icon={FolderOpen} />
        <ProjectFacts project={read.project} />
        {startable === undefined || breakdown === undefined ? null : (
          <ProjectStart
            projectId={address.projectId}
            offers={startable}
            breakdownHref={`${breakdown}${breakdown.includes("?") ? "&" : "?"}start=skeleton`}
            start={start}
          />
        )}
        {shown === undefined ? null : (
          <ImportReport
            key={shown.import_id}
            projectId={address.projectId}
            entry={shown}
            offer={offers[shown.kind]}
            start={start}
            then={shown.kind === "ms_project_schedule" ? planning : undefined}
          />
        )}
        {revisions.length === 0 ? (
          <ImportPart projectId={address.projectId} offers={offers} start={start} gap={gap} />
        ) : null}
      </Screen>
    </>
  );
}
