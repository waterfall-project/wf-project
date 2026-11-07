// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The revisions of a project (FBS-4.1, US-0210), under the banner of its reading context
 * (WF-IHM-0020): the commands of the revision the address carries, each available or naming what it
 * lacks (WF-IHM-0090), its marking wired; the history of the revisions; the comparison of two
 * marked ones, as `compareRevisions` gives it — « Écarts seulement » retaining the differences
 * alone, said in the banner (US-0700) —, read whole and reduced by `fields` to what the grid of the
 * comparison shows (US-0500, #1201) — the history read whole, whatever the server pages
 * (`readEveryPage`, #303), so that the comparison offers every marked revision —; and, of the
 * revision the address carries, its cost structures and — for the current revision, the one a rate
 * update would apply to — the rate update the API proposes. The ergonomics gathers the leaves of
 * the function on one screen.
 *
 * The service serves the history, the revision, its structures, its opening and its abandonment
 * (`listRevisions`, `getRevision`, `listCostStructures`, `createRevision`, `abandonRevision`,
 * US-0960) and its marking (`markRevision`, US-0970): the screen shows no note of the mock-up. The
 * comparison and the rate update are served by EP-07; until then the rate update the service does
 * not find is left out (#2173).
 *
 * The report of the import the address names (`?import=`, which the screen of the project carries
 * here when no revision is readable) stands above the history, as on the screen of the project
 * (`readShownImport`, #1922); an address without it is read as before.
 *
 * The screen reads once, on the server: the end of a marking is announced by the tracker of the
 * shell, which offers to reload the screen; the screen does not read itself again.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readEveryPage } from "@/api/every-page";
import { readOrFail, readUnlessRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { findOffer } from "@/components/commands/offer";
import { RevisionCommands } from "@/components/commands/object-commands";
import { ContextBanner } from "@/components/context/context-banner";
import type { Revision } from "@/components/context/read-only";
import { ImportReport } from "@/components/exchanges/import-report";
import { readShownImport } from "@/components/exchanges/shown-import";
import { differenceQuery, readDifferenceFilter } from "@/components/grid/difference-filter";
import { PendingAddress } from "@/components/grid/pending-address";
import type { Project } from "@/components/context/reading";
import { COMPARISON_FIELDS, COMPARISON_KEY } from "@/components/revisions/comparison-rows";
import {
  comparedRevisions,
  RevisionComparisonSection,
} from "@/components/revisions/revision-comparison";
import { ReferenceDesignation, RevisionHistory } from "@/components/revisions/revision-history";
import { CostStructureList, RateUpdate } from "@/components/revisions/revision-parts";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { contextAddress, pageSearch, type ProjectContext } from "@/navigation/context";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../../title";
import {
  type ProjectParams,
  type ProjectPageProps,
  projectAddress,
  readProjectScreen,
} from "../screen";

/** Title the tab with the revisions, and the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<ProjectParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functions.revisions", projectId);
}

/** The title of the screen, and the commands of the revision it reads in at the right. */
function RevisionsHeader({
  revision,
  project,
  context,
}: {
  readonly revision: Revision | undefined;
  readonly project: Project;
  readonly context: ProjectContext;
}) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.revisions")}
      icon={FUNCTION_ICONS.revisions}
      density={FUNCTION_DENSITY.revisions}
      actions={<RevisionCommands revision={revision} project={project} context={context} />}
    />
  );
}

/** The settings the account keeps for the grid of the comparison; none if it keeps none. */
async function readComparisonPreferences() {
  const session = await requestSession();
  return session?.display_preferences?.grids?.[COMPARISON_KEY] ?? undefined;
}

/**
 * What applying the rates proposed to the current revision takes, or nothing when the revision does
 * not list `apply_rate_update` — the caller may not exercise it: the command is offered as the
 * revision lists it, available or lacking the conditions it names (WF-IHM-0090, #1351).
 */
function applicable(current: Revision, projectId: string) {
  const offer = findOffer(current.available_commands, "apply_rate_update");
  return offer === undefined
    ? undefined
    : { projectId, revisionId: current.revision_id, lockVersion: current.lock_version, offer };
}

/** Render the revisions of a project, their comparison, and the parts of the one it reads in. */
export default async function RevisionsPage(props: ProjectPageProps) {
  const address = await projectAddress(props, "revisions");
  const search = pageSearch(await props.searchParams);
  const compared = comparedRevisions(search);
  // « Écarts seulement » of the comparison (US-0700): read, and said, when two revisions are compared.
  const difference = compared === undefined ? undefined : readDifferenceFilter(search);
  const client = serverClient();
  const project = { project_id: address.projectId };
  const { revisionId } = address.context;
  const [read, revisions, structures, comparison, preferences, shown] = await Promise.all([
    readProjectScreen(address),
    readEveryPage("listRevisions", (page) =>
      client.GET("/projects/{project_id}/revisions", { params: { path: project, query: page } }),
    ),
    revisionId === undefined
      ? undefined
      : readOrFail("listCostStructures", () =>
          client.GET("/projects/{project_id}/revisions/{revision_id}/structures", {
            params: { path: { ...project, revision_id: revisionId } },
          }),
        ),
    compared === undefined
      ? undefined
      : readOrFail("compareRevisions", () =>
          client.GET("/projects/{project_id}/revisions/comparison", {
            params: {
              path: project,
              query: {
                ...compared,
                fields: [...COMPARISON_FIELDS],
                ...differenceQuery(difference),
              },
            },
          }),
        ),
    compared === undefined ? undefined : readComparisonPreferences(),
    readShownImport(address.projectId, search),
  ]);
  // A marked revision is immutable (WF-REV-0020): a rate update applies to the current one. The
  // service serves no proposal before EP-07 and answers 404: the screen of the current revision is
  // rendered without one rather than not found, its commands playable (#2173).
  const current = read.revision?.status === "draft" ? read.revision : undefined;
  const rates =
    current === undefined
      ? undefined
      : await readUnlessRefused("getRateUpdateProposal", [{ status: 404 }], () =>
          client.GET("/projects/{project_id}/revisions/{revision_id}/rate-update", {
            params: { path: { ...project, revision_id: current.revision_id } },
          }),
        );
  return (
    <PendingAddress>
      <ContextBanner reading={read} difference={difference} />
      <Screen density={FUNCTION_DENSITY.revisions}>
        <RevisionsHeader revision={read.revision} project={read.project} context={read.context} />
        {shown === undefined ? null : (
          <ImportReport
            key={shown.import_id}
            projectId={address.projectId}
            entry={shown}
            start={contextAddress(address.pathname, read.context)}
          />
        )}
        <RevisionHistory revisions={revisions} context={read.context} />
        <ReferenceDesignation
          revisions={revisions}
          projectId={address.projectId}
          projectLockVersion={read.project.lock_version}
        />
        <RevisionComparisonSection
          revisions={revisions}
          action={address.pathname}
          context={read.context}
          compared={compared}
          comparison={comparison}
          difference={difference}
          preferences={preferences}
        />
        {structures === undefined ? null : <CostStructureList structures={structures} />}
        {rates === undefined || current === undefined ? null : (
          <RateUpdate proposal={rates} apply={applicable(current, address.projectId)} />
        )}
      </Screen>
    </PendingAddress>
  );
}
