// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The indicators of a project (FBS-4.8, US-0240), at the route of their function
 * (`functions.json`): the banner of the reading context (WF-IHM-0020); the indicators FBS-4.8.1 to
 * FBS-4.8.5 as the API computes them for the sub-project and at the date the address filters
 * (`getProjectIndicators`, `scope`, `as_of`), with the evolution of the indices
 * (`getIndexHistory`, WF-IND-0130).
 *
 * The indicators of a project are computed from the state In progress only (WF-IND-0010): before,
 * the API refuses them (409, `STATE_FORBIDS_OPERATION`), and the screen says so rather than coming
 * down, the evolution of the indices left unasked. Any other answer follows the rule of the reads
 * (`readOrFail`): the screen never shows a figure it did not read, and computes none.
 */
import { TriangleAlert } from "lucide-react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import { readOrFail, readUnlessRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { readProjectContext } from "@/components/context/reading";
import { ProjectIndicatorCards } from "@/components/indicators/project-indicators";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import type { PageSearchParams } from "@/navigation/context";

import { screenMetadata } from "../../../../../title";
import { type GridAddress, gridAddress } from "../grid-screen";
import type { RevisionParams } from "../page";

/** Title the tab with the function, and with the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<RevisionParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functions.projectIndicators", projectId);
}

/** The refusal of the indicators of a project not yet in progress (WF-IND-0010). */
const NOT_IN_PROGRESS = [{ status: 409, code: "STATE_FORBIDS_OPERATION" }] as const;

/**
 * The indicators of the project for the sub-project and at the date the address filters, then
 * the evolution of its indices; neither when the project is not yet in progress, the evolution
 * left unasked.
 */
async function readIndicators({ revision, context }: GridAddress) {
  const client = serverClient();
  const path = { project_id: revision.projectId };
  const scope = context.parameters.get("subproject_id");
  const asOf = context.parameters.get("as_of");
  const query = {
    ...(scope === null ? {} : { scope }),
    ...(asOf === null ? {} : { as_of: asOf }),
  };
  const indicators = await readUnlessRefused("getProjectIndicators", NOT_IN_PROGRESS, () =>
    client.GET("/projects/{project_id}/indicators", { params: { path, query } }),
  );
  if (indicators === undefined) {
    return undefined;
  }
  const history = await readOrFail("getIndexHistory", () =>
    client.GET("/projects/{project_id}/indicators/index-history", { params: { path } }),
  );
  return { indicators, history };
}

/** What the screen says when the API does not compute the indicators of the project yet. */
function NotInProgress() {
  const t = useTranslations("projectIndicators.notInProgress");
  return (
    <Alert>
      <TriangleAlert aria-hidden="true" />
      <AlertTitle>{t("title")}</AlertTitle>
      <AlertDescription>{t("explanation")}</AlertDescription>
    </Alert>
  );
}

/** The header of the screen: the name and the icon of the function. */
function IndicatorsHeader() {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.projectIndicators")}
      icon={FUNCTION_ICONS.project_indicators}
      density={FUNCTION_DENSITY.project_indicators}
    />
  );
}

/** Render the indicators of a project and the evolution of its indices. */
export default async function IndicatorsPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "indicators");
  const [reading, figures] = await Promise.all([
    readProjectContext(at.pathname, at.context),
    readIndicators(at),
  ]);
  if (reading === "not_found") {
    notFound();
  }
  return (
    <>
      <ContextBanner reading={reading} />
      <Screen density={FUNCTION_DENSITY.project_indicators}>
        <IndicatorsHeader />
        {figures === undefined ? <NotInProgress /> : <ProjectIndicatorCards {...figures} />}
      </Screen>
    </>
  );
}
