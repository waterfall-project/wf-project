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

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { readProjectContext } from "@/components/context/reading";
import { readValues } from "@/components/grid/filters";
import { PendingAddress } from "@/components/grid/pending-address";
import { type GridQuery, readGridQuery } from "@/components/grid/query";
import { readRisk, RISK_STATES, type RiskState, STATES } from "@/components/risks/address";
import { ProvisionSummary } from "@/components/risks/provision-totals";
import { RiskCoverageSummary } from "@/components/risks/risk-coverage";
import { RiskDetail } from "@/components/risks/risk-detail";
import {
  RISK_GRID,
  RISK_SORT_COLUMNS,
  riskRow,
  type RiskRows,
  type RiskSortColumn,
} from "@/components/risks/risk-grid";
import { RiskMatrixView } from "@/components/risks/risk-matrix";
import { RisksGrid } from "@/components/risks/risks-grid";
import { RiskStateFilter } from "@/components/risks/state-filter";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import type { PageSearchParams } from "@/navigation/context";
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

/** The title of the screen, and how many risks the grid holds. */
function RisksHeader({ count }: { readonly count: number }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.risks")}
      icon={FUNCTION_ICONS.risks}
      density={FUNCTION_DENSITY.risks}
      subtitle={t("risks.summary", { risks: count })}
    />
  );
}

/** The aside of the grid: the detail of a risk opened, or how to open one. */
function DetailHint() {
  const t = useTranslations("risks.detail");
  return <p className="text-sm text-muted-foreground">{t("hint")}</p>;
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
  const settings = requestSession().then(
    (session) => session?.display_preferences?.grids?.[RISK_GRID.key] ?? undefined,
  );
  const asked = settings.then((kept) => readGridQuery(at.address, RISK_SORT_COLUMNS, kept?.sort));
  const [reading, risks, coverage, matrix, detail, preferences, query] = await Promise.all([
    // The risks take neither a sub-project nor a date: the banner shows no filter (#302).
    readProjectContext(at.pathname, at.context, []),
    readRisks(at, states, asked),
    readCoverage(at),
    readMatrix(at),
    readDetail(at, readRisk(at.address)),
    settings,
    asked,
  ]);
  if (reading === "not_found") {
    notFound();
  }
  return (
    <>
      <ContextBanner reading={reading} />
      {/* The filter, the grid and the links compose the changes they make to the address. */}
      <PendingAddress>
        <Screen density={FUNCTION_DENSITY.risks} fill>
          <RisksHeader count={risks.items.length} />
          <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
            <div className="flex flex-wrap gap-x-12 gap-y-3">
              <ProvisionSummary totals={risks.totals} />
              <RiskCoverageSummary coverage={coverage} />
            </div>
            <RiskStateFilter states={states} />
          </div>
          <div className="flex min-h-0 flex-1 flex-col gap-4 lg:flex-row">
            <div className="flex min-h-0 min-w-0 flex-1 flex-col">
              <RisksGrid risks={risks} query={query} preferences={preferences} />
            </div>
            <aside className="flex shrink-0 flex-col gap-4 lg:w-96 lg:overflow-y-auto">
              <RiskMatrixView matrix={matrix} />
              {detail === undefined ? <DetailHint /> : <RiskDetail {...detail} />}
            </aside>
          </div>
        </Screen>
      </PendingAddress>
    </>
  );
}
