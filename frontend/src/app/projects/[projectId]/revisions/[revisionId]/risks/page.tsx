// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The risks of a revision (WF-RIS-0040, US-0230), at the route of their function
 * (`functions.json`), each read for the revision of the route (`revision_id`), which fixes a
 * version of their own estimate, and so their severity, their provision and their cell
 * (WF-RIS-0030): the banner of the reading context (WF-IHM-0020); the totals of the provisions
 * of the risks retained, by state and their general total, with the risk reserve of the reference
 * revision; the coverage of the risks in the revision (`getProjectRiskCoverage`, WF-RIS-0050); the
 * filter by state; the grid of the risks, sorted, searched and filtered by the server as the
 * address asks (`sort_by`, `search`, `states`, under the names of the contract); the risk matrix
 * of the revision; and, when the address names one (`risk`), the detail of a risk — its notes, its
 * provision line, the history of its reviews. Every figure as the API gives it: the front
 * computes, sorts and filters nothing. A read the API refuses, or cannot answer, is thrown for the
 * pages of the shell to say.
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { findOffer } from "@/components/commands/offer";
import { ContextBanner } from "@/components/context/context-banner";
import { type ProjectReading, readProjectContext } from "@/components/context/reading";
import { readValues } from "@/components/grid/filters";
import { PendingAddress } from "@/components/grid/pending-address";
import { type GridQuery, readGridQuery } from "@/components/grid/query";
import { readRisk, RISK_STATES, type RiskState, STATES } from "@/components/risks/address";
import { FiguresGrid } from "@/components/figures-card";
import { ProvisionSummary } from "@/components/risks/provision-totals";
import { RiskCoverageSummary } from "@/components/risks/risk-coverage";
import { readProvisionOptions } from "@/components/risks/provision-options";
import { IdentifyRisk } from "@/components/risks/risk-commands";
import { RiskDetail } from "@/components/risks/risk-detail";
import {
  RISK_GRID,
  RISK_SORT_COLUMNS,
  riskRow,
  type RiskRows,
  type RiskSortColumn,
} from "@/components/risks/risk-grid";
import { ProjectRiskMatrix } from "@/components/risks/risk-bubble-chart";
import type { RiskMatrix } from "@/components/risks/risk-matrix";
import { RisksGrid } from "@/components/risks/risks-grid";
import { RiskStateFilter } from "@/components/risks/state-filter";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import type { PageSearchParams } from "@/navigation/context";
import { functionHref, functionOf } from "@/navigation/functions";
import { requestSession } from "@/session/request";

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
  return screenMetadata("functions.risks", projectId);
}

/**
 * The risks of the revision as the address asks them — sorted, searched, filtered on states —,
 * and the totals of their provisions, those of the risks retained; of each risk, the fields the
 * grid reads alone (`riskRow`).
 */
async function readRisks(
  { revision }: GridAddress,
  states: readonly RiskState[],
  asked: Promise<GridQuery<RiskSortColumn>>,
): Promise<RiskRows> {
  const { sort, search } = await asked;
  const answer = await readOrFail("listRisks", () =>
    serverClient().GET("/projects/{project_id}/risks", {
      params: {
        path: { project_id: revision.projectId },
        query: {
          revision_id: revision.revisionId,
          ...(states.length === 0 ? {} : { states: [...states] }),
          ...(search === undefined ? {} : { search }),
          ...(sort === undefined ? {} : { sort_by: sort.column, sort_order: sort.order }),
        },
      },
    }),
  );
  return { items: answer.items.map(riskRow), totals: answer.totals };
}

/** The coverage of the risks in the revision: the reserve against what the risks cost. */
async function readCoverage({ revision }: GridAddress) {
  return readOrFail("getProjectRiskCoverage", () =>
    serverClient().GET("/projects/{project_id}/risks/coverage", {
      params: {
        path: { project_id: revision.projectId },
        query: { revision_id: revision.revisionId },
      },
    }),
  );
}

/** The risk matrix of the revision. */
async function readMatrix({ revision }: GridAddress) {
  return readOrFail("getProjectRiskMatrix", () =>
    serverClient().GET("/projects/{project_id}/risks/matrix", {
      params: {
        path: { project_id: revision.projectId },
        query: { revision_id: revision.revisionId },
      },
    }),
  );
}

/**
 * The risk the address names, and the history of its reviews, as the revision holds them; none
 * when the address names none. A risk the API does not find is not found, as any object of the
 * address.
 */
async function readDetail({ revision }: GridAddress, risk: string | undefined) {
  if (risk === undefined) {
    return undefined;
  }
  const client = serverClient();
  const params = {
    path: { project_id: revision.projectId, risk_id: risk },
    query: { revision_id: revision.revisionId },
  };
  const [read, reviews] = await Promise.all([
    readOrFail("getRisk", () => client.GET("/projects/{project_id}/risks/{risk_id}", { params })),
    readOrFail("listRiskReviews", () =>
      client.GET("/projects/{project_id}/risks/{risk_id}/reviews", { params }),
    ),
  ]);
  return { risk: read, reviews };
}

/** The title of the screen, how many risks the grid holds, and its commands. */
function RisksHeader({ count, actions }: { readonly count: number; readonly actions: ReactNode }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.risks")}
      icon={FUNCTION_ICONS.risks}
      density={FUNCTION_DENSITY.risks}
      subtitle={t("risks.summary", { risks: count })}
      actions={actions}
    />
  );
}

/**
 * The matrix of the revision as a bubble chart over the whole width of the screen, its exported
 * image naming the project, the revision and the date of the calculation of the coverage, which
 * the matrix is read with.
 */
function RiskMatrixSection({
  reading,
  matrix,
  states,
  computedAt,
}: {
  readonly reading: ProjectReading;
  readonly matrix: RiskMatrix;
  readonly states: readonly RiskState[];
  readonly computedAt: string;
}) {
  const t = useTranslations("contextBanner");
  const { project, revision } = reading;
  return (
    <ProjectRiskMatrix
      matrix={matrix}
      states={states}
      provenance={{
        project: project.label,
        code: project.code ?? project.project_id,
        revision: revision?.version_name ?? t("currentRevision"),
      }}
      computedAt={computedAt}
    />
  );
}

/**
 * Render the risks of a revision: their totals and their coverage, their filter, their grid, their
 * matrix.
 */
export default async function RisksPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "risks");
  const states = readValues(at.address, STATES, RISK_STATES);
  const session = requestSession();
  const settings = session.then(
    (kept) => kept?.display_preferences?.grids?.[RISK_GRID.key] ?? undefined,
  );
  const asked = settings.then((kept) => readGridQuery(at.address, RISK_SORT_COLUMNS, kept?.sort));
  // The risks take neither a sub-project nor a date: the banner shows no filter (#302).
  const reading = readProjectContext(at.pathname, at.context, []);
  // « Identifier un risque » as the revision lists `declare_risk`, and the modification of the risk
  // shown, as it lists `update`: the choices of the provision are read as soon as the revision and
  // the risk are, beside the other reads, when either command is available.
  const declare = reading.then((read) =>
    read === "not_found" || read.revision === undefined
      ? undefined
      : findOffer(read.revision.available_commands, "declare_risk"),
  );
  const shown = readDetail(at, readRisk(at.address));
  const options = Promise.all([declare, shown]).then(([offer, read]) =>
    offer?.is_available === true ||
    findOffer(read?.risk.available_commands ?? [], "update")?.is_available === true
      ? readProvisionOptions(at.revision.projectId, at.revision.revisionId)
      : undefined,
  );
  const [read, risks, coverage, matrix, detail, preferences, query, offer, choices, kept] =
    await Promise.all([
      reading,
      readRisks(at, states, asked),
      readCoverage(at),
      readMatrix(at),
      shown,
      settings,
      asked,
      declare,
      options,
      session,
    ]);
  if (read === "not_found") {
    notFound();
  }
  // The own estimate of a risk opens in the estimate of the revision, for a session that reads it.
  const estimate = kept?.permissions.includes("estimate.read")
    ? functionHref(functionOf("estimate"), at.context)
    : undefined;
  return (
    <>
      <ContextBanner reading={read} />
      {/* The filter, the grid and the links compose the changes they make to the address. */}
      <PendingAddress>
        <Screen density={FUNCTION_DENSITY.risks} fillWide>
          <RisksHeader
            count={risks.items.length}
            actions={
              <IdentifyRisk
                projectId={at.revision.projectId}
                offer={offer}
                options={choices}
                estimate={estimate}
              />
            }
          />
          <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
            <FiguresGrid className="min-w-0 grow basis-[40rem]">
              <ProvisionSummary totals={risks.totals} />
              <RiskCoverageSummary coverage={coverage} context={coverage.context} />
            </FiguresGrid>
            <RiskStateFilter states={states} />
          </div>
          <RiskMatrixSection
            reading={read}
            matrix={matrix}
            states={states}
            computedAt={coverage.context.computed_at}
          />
          {/* The detail of a risk, beside the grid, keeps the height to read it in: the window too
              low for the chart, the grid and the detail scrolls the page. */}
          <div
            className={`flex flex-col gap-4 lg:flex-1 lg:flex-row ${detail === undefined ? "lg:min-h-0" : "lg:min-h-96"}`}
          >
            <div className="flex min-w-0 flex-col lg:min-h-0 lg:flex-1">
              <RisksGrid risks={risks} query={query} preferences={preferences} />
            </div>
            {detail === undefined ? null : (
              <aside className="flex shrink-0 flex-col gap-4 lg:w-96 lg:overflow-y-auto">
                <RiskDetail {...detail} projectId={at.revision.projectId} options={options} />
              </aside>
            )}
          </div>
        </Screen>
      </PendingAddress>
    </>
  );
}
