// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The revisions of a project (FBS-4.1, US-0210), under the banner of its reading context
 * (WF-IHM-0020): the commands of the revision the address carries, each available or naming what
 * it lacks (WF-IHM-0090), its marking wired; the history of the revisions; the comparison of two
 * marked ones, as `compareRevisions` gives it; and, of the revision the address carries, its cost
 * structures and — for the current revision, the one a rate update would apply to — the rate
 * update the API proposes. The ergonomics gathers the leaves of the function on one screen.
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
import {
  comparedRevisions,
  RevisionComparisonSection,
} from "@/components/revisions/revision-comparison";
import { RevisionHistory } from "@/components/revisions/revision-history";
import { CostStructureList, RateUpdate } from "@/components/revisions/revision-parts";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { pageSearch } from "@/navigation/context";

import { screenMetadata } from "../../../title";
import {
  type ProjectParams,
  type ProjectPageProps,
  projectAddress,
  readProjectScreen,
} from "../screen";

// A project marks a few revisions a year: the history holds whole in the largest page the
// contract allows.
const HISTORY_LIMIT = 500;

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
function RevisionsHeader({ revision }: { readonly revision: Revision | undefined }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.revisions")}
      icon={FUNCTION_ICONS.revisions}
      density={FUNCTION_DENSITY.revisions}
      actions={revision === undefined ? undefined : <RevisionCommands revision={revision} />}
    />
  );
}

/** Render the revisions of a project, their comparison, and the parts of the one it reads in. */
export default async function RevisionsPage(props: ProjectPageProps) {
  const address = await projectAddress(props, "revisions");
  const compared = comparedRevisions(pageSearch(await props.searchParams));
  const client = serverClient();
  const project = { project_id: address.projectId };
  const { revisionId } = address.context;
  const [read, revisions, structures, comparison] = await Promise.all([
    readProjectScreen(address),
    readOrFail("listRevisions", () =>
      client.GET("/projects/{project_id}/revisions", {
        params: { path: project, query: { limit: HISTORY_LIMIT } },
      }),
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
            params: { path: project, query: compared },
          }),
        ),
  ]);
  // A marked revision is immutable (WF-REV-0020): a rate update applies to the current one.
  const current = read.revision?.status === "draft" ? read.revision : undefined;
  const rates =
    current === undefined
      ? undefined
      : await readOrFail("getRateUpdateProposal", () =>
          client.GET("/projects/{project_id}/revisions/{revision_id}/rate-update", {
            params: { path: { ...project, revision_id: current.revision_id } },
          }),
        );
  return (
    <>
      <ContextBanner reading={read} />
      <Screen density={FUNCTION_DENSITY.revisions}>
        <RevisionsHeader revision={read.revision} />
        <RevisionHistory
          revisions={revisions.items}
          total={revisions.meta.total}
          context={read.context}
        />
        <RevisionComparisonSection
          revisions={revisions.items}
          action={address.pathname}
          context={read.context}
          compared={compared}
          comparison={comparison}
        />
        {structures === undefined ? null : <CostStructureList structures={structures} />}
        {rates === undefined ? null : <RateUpdate proposal={rates} />}
      </Screen>
    </>
  );
}
