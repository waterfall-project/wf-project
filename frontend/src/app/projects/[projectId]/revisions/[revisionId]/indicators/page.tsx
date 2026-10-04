// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The indicators of a project (FBS-4.8, US-0240), at the route of their function
 * (`functions.json`): the banner of the reading context (WF-IHM-0020); the indicators FBS-4.8.1 to
 * FBS-4.8.5 as the API computes them for the sub-project and at the date the address filters
 * (`getProjectIndicators`, `scope`, `as_of`), with the evolution of the indices
 * (`getIndexHistory`, WF-IND-0130); and the tracking of the milestones, the time/time diagram
 * (`getMilestoneTracking`, WF-IND-0090).
 *
 * The indicators of a project are computed from the state In progress only (WF-IND-0010): before,
 * the API refuses them (409), and the screen says so rather than coming down. A tracking of the
 * milestones the API does not find is said unavailable, the rest of the screen shown. Any other
 * answer follows the rule of the reads (`readOrFail`): the screen never shows a figure it did not
 * read, and computes none.
 */
import { TriangleAlert } from "lucide-react";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import { Unreachable } from "@/api/client";
import { isGatewayFailure, readOrFail, refusalOf } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { CalculationDate } from "@/components/context/indicator";
import { readProjectContext } from "@/components/context/reading";
import { type MilestoneTracking, MilestoneChart } from "@/components/indicators/milestone-chart";
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

/**
 * Read an answer the screen can do without: its data; `undefined` on the status the screen
 * expects may come — the indicators of a project not yet in progress, a tracking not found.
 * Any other answer follows the rule of the reads.
 */
async function readUnless<T>(
  operation: string,
  expected: number,
  call: () => Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T | undefined> {
  const answer = await call();
  const { ok, status } = answer.response;
  if (ok) {
    return answer.data;
  }
  if (status === expected) {
    return undefined;
  }
  if (status === 404) {
    notFound();
  }
  if (isGatewayFailure(answer.response, answer.error)) {
    throw new Unreachable();
  }
  throw refusalOf(operation, status, answer.error);
}

/** The indicators, the evolution of the indices and the tracking of the milestones. */
async function readIndicators({ revision, context }: GridAddress) {
  const client = serverClient();
  const path = { project_id: revision.projectId };
  const scope = context.parameters.get("subproject_id");
  const asOf = context.parameters.get("as_of");
  const query = {
    ...(scope === null ? {} : { scope }),
    ...(asOf === null ? {} : { as_of: asOf }),
  };
  return Promise.all([
    readUnless("getProjectIndicators", 409, () =>
      client.GET("/projects/{project_id}/indicators", { params: { path, query } }),
    ),
    readOrFail("getIndexHistory", () =>
      client.GET("/projects/{project_id}/indicators/index-history", { params: { path } }),
    ),
    readUnless("getMilestoneTracking", 404, () =>
      client.GET("/projects/{project_id}/indicators/milestone-tracking", { params: { path } }),
    ),
  ]);
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

/** The tracking of the milestones: its diagram, that none is tracked, or that it is unavailable. */
function Milestones({ tracking }: { readonly tracking: MilestoneTracking | undefined }) {
  const t = useTranslations("projectIndicators.milestones");
  let content;
  if (tracking === undefined) {
    content = <p className="text-muted-foreground">{t("unavailable")}</p>;
  } else if (tracking.milestones.length === 0) {
    content = <p className="text-muted-foreground">{t("none")}</p>;
  } else {
    content = <MilestoneChart tracking={tracking} />;
  }
  return (
    <section aria-labelledby="milestone-tracking" className="space-y-2">
      <h2 id="milestone-tracking" className="text-lg font-semibold">
        {t("title")}
      </h2>
      {tracking === undefined ? null : <CalculationDate context={tracking.context} />}
      {content}
    </section>
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

/** Render the indicators of a project, the evolution of its indices, its milestones. */
export default async function IndicatorsPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "indicators");
  const [reading, [indicators, history, tracking]] = await Promise.all([
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
        {indicators === undefined ? (
          <NotInProgress />
        ) : (
          <ProjectIndicatorCards indicators={indicators} history={history} />
        )}
        <Milestones tracking={tracking} />
      </Screen>
    </>
  );
}
