// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A project (US-0210), second step of the witness path (US-0080): the banner of its reading
 * context (WF-IHM-0020), its label, what it is — its code, its state, its order, its
 * description —, and its revisions, each opened in the reading context of the address, the filters
 * it carries kept (WF-IHM-0010) — or, when it has none yet, that it has none, with the way to the
 * function of its revisions when the session may read them, and the imports the project offers:
 * no address of a revision reaches the screen of the imports yet, and an import creates the
 * revision it applies to (WF-INTF-0090, #332) — the report of the import the address names
 * (`import`) shown above them, applied or abandoned there. A project the API does not find is not
 * found, as at the other screens of a project. Nothing is offered to modify it: its form belongs to
 * the epic of its domain.
 */
import { FolderOpen, GitBranch } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { readEveryPage } from "@/api/every-page";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { ImportPart } from "@/components/exchanges/import-part";
import { readMappingGap } from "@/components/exchanges/mapping-gap";
import { ImportReport } from "@/components/exchanges/import-report";
import { importOffers } from "@/components/exchanges/offers";
import { readShownImport } from "@/components/exchanges/shown-import";
import { ProjectFacts } from "@/components/projects/project-facts";
import { ProjectStart } from "@/components/projects/project-start";
import { startOffers } from "@/components/projects/start-offers";
import { type NamedRevision, useRevisionName } from "@/components/revisions/revision-history";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { NoRevisions } from "@/components/system/empty-states";
import { contextAddress, contextQuery, pageSearch } from "@/navigation/context";
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

/** The revisions of a project, each a link to it, or that it has none. */
function Revisions({
  projectId,
  revisions,
  filters,
  way,
}: {
  readonly projectId: string;
  readonly revisions: readonly NamedRevision[];
  /** The filters of the address, which a revision opened keeps: `?subproject_id=…`, or nothing. */
  readonly filters: string;
  /** The way to the function of the revisions, when the session may read them. */
  readonly way: string | undefined;
}) {
  const t = useTranslations();
  const revisionName = useRevisionName();
  return (
    <section aria-label={t("projectFacts.revisions")} className="space-y-2">
      <h2 className="flex items-center gap-2 text-base font-semibold">
        <GitBranch aria-hidden="true" className="size-4 shrink-0 text-muted-foreground" />
        {t("projectFacts.revisions")}
      </h2>
      {revisions.length === 0 ? (
        <NoRevisions revisions={way} />
      ) : (
        <ul className="space-y-1 text-sm">
          {revisions.map((revision) => (
            <li key={revision.revision_id}>
              <Link
                href={`/projects/${projectId}/revisions/${revision.revision_id}${filters}`}
                className="underline-offset-4 hover:underline"
              >
                {revisionName(revision)}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

/** Render a project, what it is, and links to its revisions. */
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
  // The way to the revisions is offered as the navigation offers them: to a session that
  // may read them.
  const mayReadRevisions = session?.permissions.includes("revisions.read") === true;
  const offers = importOffers(read.project);
  // Only a project without a revision shows its imports here.
  const gap =
    revisions.length === 0 ? await readMappingGap(offers, session?.permissions) : undefined;
  // The address of the screen without a report, its context kept.
  const start = contextAddress(address.pathname, read.context);
  // The start of the planning: read at the server, from the revision in progress, which the list of the revisions carries whole (WF-PRJ-0030).
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
        <Revisions
          projectId={address.projectId}
          revisions={revisions}
          filters={contextQuery(read.context, false)}
          way={mayReadRevisions ? functionHref(functionOf("revisions"), read.context) : undefined}
        />
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
