// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The revisions of a project (FBS-4.1, US-0210), under the banner of its reading context
 * (WF-IHM-0020): the commands of the revision the address carries, each available or naming what it
 * lacks (WF-IHM-0090), its marking wired; the history of the revisions, read whole, whatever the
 * server pages (`listProjectRevisions`, #303). The screen holds that one card (US-2370): the
 * comparison of two revisions is read in the grids, to which each marked revision of the history
 * leads, as the base of the comparison (« Comparer à la révision lue »), and the screen reads no
 * `compareRevisions`.
 *
 * The service serves the history, the revision, its opening and its abandonment (`listRevisions`,
 * `getRevision`, `createRevision`, `abandonRevision`, US-0960) and its marking (`markRevision`,
 * US-0970): the screen shows no note of the mock-up.
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

import { RevisionCommands } from "@/components/commands/object-commands";
import { ContextBanner } from "@/components/context/context-banner";
import type { Revision } from "@/components/context/read-only";
import { ImportReport } from "@/components/exchanges/import-report";
import { readShownImport } from "@/components/exchanges/shown-import";
import { PendingAddress } from "@/components/grid/pending-address";
import type { Project } from "@/components/context/reading";
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

/** Render the revisions of a project: their history, and the commands of the one read. */
export default async function RevisionsPage(props: ProjectPageProps) {
  const address = await projectAddress(props, "revisions");
  const search = pageSearch(await props.searchParams);
  const [read, revisions, session, shown] = await Promise.all([
    readProjectScreen(address),
    // The same read as the banner's, once per request.
    listProjectRevisions(address.projectId),
    requestSession(),
    readShownImport(address.projectId, search),
  ]);
  return (
    <PendingAddress>
      <ContextBanner reading={read} />
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
          permissions={session?.permissions ?? []}
          creation={revisionCreation(read.project)}
        />
      </Screen>
    </PendingAddress>
  );
}
