// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The revisions of a project (FBS-4.1, US-0210), under the banner of its reading context
 * (WF-IHM-0020): the commands of the revision the address carries, each available or naming what it
 * lacks (WF-IHM-0090), its marking wired; the history of the revisions; the comparison of two
 * marked ones, as `compareRevisions` gives it — « Écarts seulement » retaining the differences
 * alone, said in the banner (US-0700) —, read whole and reduced by `fields` to what the grid of the
 * comparison shows (US-0500, #1201) — the history read whole, whatever the server pages
 * (`listProjectRevisions`, #303), so that the comparison offers every marked revision. The
 * ergonomics gathers the leaves of the function on one screen.
 *
 * The service serves the history, the revision, its opening and its abandonment (`listRevisions`,
 * `getRevision`, `createRevision`, `abandonRevision`, US-0960), its marking (`markRevision`,
 * US-0970) and the comparison (`compareRevisions`, US-1530): the screen shows no note of the
 * mock-up.
 *
 * The opening of the current revision is the principal command of the card of the history, filled
 * (US-2130); the commands of the revision it reads in stay at the right of the title of the screen.
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

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
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
import { RevisionHistory, revisionCreation } from "@/components/revisions/revision-history";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { contextAddress, pageSearch, type ProjectContext } from "@/navigation/context";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../../title";
import {
  listProjectRevisions,
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

/** Render the revisions of a project and their comparison. */
export default async function RevisionsPage(props: ProjectPageProps) {
  const address = await projectAddress(props, "revisions");
  const search = pageSearch(await props.searchParams);
  const compared = comparedRevisions(search);
  // « Écarts seulement » of the comparison (US-0700): read, and said, when two revisions are compared.
  const difference = compared === undefined ? undefined : readDifferenceFilter(search);
  const client = serverClient();
  const project = { project_id: address.projectId };
  const [read, revisions, comparison, preferences, shown] = await Promise.all([
    readProjectScreen(address),
    // The same read as the banner's, once per request.
    listProjectRevisions(address.projectId),
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
        <RevisionHistory
          revisions={revisions}
          context={read.context}
          projectLockVersion={read.project.lock_version}
          creation={revisionCreation(read.project)}
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
      </Screen>
    </PendingAddress>
  );
}
