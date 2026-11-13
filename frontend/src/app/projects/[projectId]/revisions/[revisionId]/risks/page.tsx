// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The risks of a revision (WF-RIS-0040, US-0230), at the route of their function
 * (`functions.json`), each read for the revision of the route (`revision_id`), which fixes a
 * version of their own estimate, and so their severity, their provision and their cell
 * (WF-RIS-0030): the banner of the reading context (WF-IHM-0020); the totals of the provisions
 * of the risks retained, by state and their general total, with the risk reserve of the reference
 * revision; the coverage of the risks in the revision (`getProjectRiskCoverage`, WF-RIS-0050); the
 * filter by state; the grid of the risks, a page of them, sorted, searched, filtered and paged by
 * the server as the address asks (`sort_by`, `search`, `states`, `limit`, `offset`, under the names
 * of the contract), with its pages and « Lignes par page » under it; the risk matrix
 * of the revision; and, when the address names one (`risk`), the detail of a risk — its notes, its
 * provision line, the history of its reviews. Every figure as the API gives it: the front
 * computes, sorts and filters nothing. A read the API refuses, or cannot answer, is thrown for the
 * pages of the shell to say.
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import {
  OPTIONAL_READ_REFUSALS,
  readOrFail,
  readOrRefused,
  readUnlessRefused,
} from "@/api/problem";
import { serverClient } from "@/api/server";
import { findOffer } from "@/components/commands/offer";
import { ContextBanner } from "@/components/context/context-banner";
import { type ProjectReading, readProjectContext } from "@/components/context/reading";
import { readPage } from "@/components/costs/address";
import { readValues } from "@/components/grid/filters";
import { ListPages } from "@/components/grid/list-pages";
import { PendingAddress } from "@/components/grid/pending-address";
import {
  CONTRACT_ADDRESS,
  limited,
  OFFSET,
  type GridQuery,
  readGridQuery,
} from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import {
  readRisk,
  readRiskFilters,
  RISK_STATES,
  RISK_ZONES,
  RISKS_LIST,
  type RiskFilters,
  riskFilterQuery,
  type RiskState,
  STATES,
  universalDay,
  ZONES,
} from "@/components/risks/address";
import { RiskFilterPanel } from "@/components/risks/risk-filters";
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
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { MockupNotice } from "@/components/shell/mockup-notice";
import type { PageSearchParams } from "@/navigation/context";
import { functionHref, functionOf } from "@/navigation/functions";
import type { ListPage } from "@/navigation/pages";
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

type FieldProblem = components["schemas"]["FieldProblem"];

/** The refusal of a filter of a column the server cannot apply (`listRisks`, 422). */
const FILTERS_REFUSED = [{ status: 422, code: "VALIDATION_FAILED" }] as const;

/** The risks of a page, or the filters the server refused, said at their field. */
type RisksRead =
  | ({ readonly kind: "read"; readonly page: ListPage } & RiskRows)
  | { readonly kind: "refused"; readonly fields: readonly FieldProblem[] };

/**
 * A page of the risks of the revision as the address asks it — sorted, searched, filtered on
 * states, from its place —, and the totals of their provisions, those of every risk retained, not
 * of the page; of each risk, the fields the grid reads alone (`riskRow`).
 */
async function readRisks(
  { revision, address }: GridAddress,
  states: readonly RiskState[],
  filters: RiskFilters,
  asked: Promise<GridQuery<RiskSortColumn>>,
): Promise<RisksRead> {
  const query = await asked;
  const { sort, search } = query;
  const offset = readPage(address, OFFSET);
  const answer = await readOrRefused("listRisks", FILTERS_REFUSED, () =>
    serverClient().GET("/projects/{project_id}/risks", {
      params: {
        path: { project_id: revision.projectId },
        query: {
          revision_id: revision.revisionId,
          ...limited(query),
          ...(offset === 0 ? {} : { offset }),
          ...(states.length === 0 ? {} : { states: [...states] }),
          ...riskFilterQuery(filters),
          ...(search === undefined ? {} : { search }),
          ...(sort === undefined ? {} : { sort_by: sort.column, sort_order: sort.order }),
        },
      },
    }),
  );
  if (answer.kind === "refused") {
    return { kind: "refused", fields: answer.problem.fields ?? [] };
  }
  const { items, totals, meta } = answer.data;
  return { kind: "read", items: items.map(riskRow), totals, page: meta };
}

/** The day of the last marking of the project, the latest revision marked (`listRevisions`). */
async function readLastMarkedOn({ revision }: GridAddress): Promise<string | undefined> {
  // A shortcut the screen can do without: a session that may not list the revisions, or a project
  // without them, loses the shortcut and keeps the register (`readUnlessRefused`).
  const revisions = await readUnlessRefused("listRevisions", OPTIONAL_READ_REFUSALS, () =>
    serverClient().GET("/projects/{project_id}/revisions", {
      params: { path: { project_id: revision.projectId }, query: { status: ["marked"], limit: 1 } },
    }),
  );
  // The API lists the most recent first. The day is the one of the instant in universal time, the
  // zone in which the front reads and writes every date (`TIME_ZONE`, `i18n/format.ts`): a marking
  // at 00:30 in Paris is of the day before, and `last_review_on_to` is inclusive.
  const markedAt = revisions?.items.find((each) => each.marked_at !== null)?.marked_at;
  return markedAt === null || markedAt === undefined ? undefined : universalDay(markedAt);
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

/**
 * The estimate of the revision, in its context, for a session that reads it — where the own
 * estimate of a risk opens —, and where what came of a risk occurred is read: the estimate, or the
 * planning for a session that does not read it, nowhere when it reads neither.
 */
function gridsOf(
  permissions: readonly string[] | undefined,
  { context }: GridAddress,
): { readonly estimate: string | undefined; readonly occurred: string | undefined } {
  const estimate = permissions?.includes("estimate.read")
    ? functionHref(functionOf("estimate"), context)
    : undefined;
  const planning = permissions?.includes("planning.read")
    ? functionHref(functionOf("planning"), context)
    : undefined;
  return { estimate, occurred: estimate ?? planning };
}

/** What stands for the grid when the server refused a filter of a column (422), the risks unread. */
function FiltersRefused() {
  const t = useTranslations("risks.filters");
  return <p className="text-sm text-destructive">{t("refused")}</p>;
}

/** The fields the server refused of the filters; none when it read the risks. */
function refusedFields(risks: RisksRead): readonly FieldProblem[] {
  return risks.kind === "refused" ? risks.fields : [];
}

/** The grid of the risks and its pages, or that the server refused the filters asked. */
function RisksBlock({
  risks,
  query,
  preferences,
  originGrid,
  states,
  filters,
  lastMarkedOn,
  panel,
}: {
  readonly risks: RisksRead;
  readonly query: GridQuery<RiskSortColumn>;
  readonly preferences: GridPreferences | undefined;
  readonly originGrid: string | undefined;
  readonly states: readonly RiskState[];
  readonly filters: RiskFilters;
  /** The day of the last marking of the project, if it has marked a revision. */
  readonly lastMarkedOn: string | undefined;
  /** The filters, in the bar of the grid, or above the sentence that stands for it. */
  readonly panel: ReactNode;
}) {
  if (risks.kind === "refused") {
    return (
      <>
        {panel}
        <FiltersRefused />
      </>
    );
  }
  return (
    <>
      <RisksGrid
        risks={risks}
        query={query}
        preferences={preferences}
        originGrid={originGrid}
        states={states}
        filters={filters}
        lastMarkedOn={lastMarkedOn}
        panel={panel}
      />
      <ListPages
        list={RISKS_LIST}
        texts="risks.pages"
        page={risks.page}
        shown={risks.items.length}
      />
    </>
  );
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
  computedAt,
  folded,
}: {
  readonly reading: ProjectReading;
  readonly matrix: RiskMatrix;
  readonly computedAt: string;
  readonly folded: boolean;
}) {
  const t = useTranslations("contextBanner");
  const { project, revision } = reading;
  return (
    <ProjectRiskMatrix
      matrix={matrix}
      provenance={{
        project: project.label,
        code: project.code ?? project.project_id,
        revision: revision?.version_name ?? t("currentRevision"),
      }}
      computedAt={computedAt}
      folded={folded}
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
  const filters = readRiskFilters(at.address, readValues(at.address, ZONES, RISK_ZONES));
  const session = requestSession();
  const settings = session.then(
    (kept) => kept?.display_preferences?.grids?.[RISK_GRID.key] ?? undefined,
  );
  const asked = settings.then((kept) =>
    readGridQuery(at.address, RISK_SORT_COLUMNS, kept?.sort, CONTRACT_ADDRESS, kept?.page_size),
  );
  // The risks take neither a sub-project nor a date: the banner shows no filter (#302).
  const reading = readProjectContext(at.pathname, at.context, []);
  // « Identifier un risque » as the revision lists `declare_risk`, and the modification and the review
  // of the risk shown, as it lists `update` and `review`: the choices of the provision are read as
  // soon as the revision and the risk are, beside the other reads, when any of these commands is available.
  const declare = reading.then((read) =>
    read === "not_found" || read.revision === undefined
      ? undefined
      : findOffer(read.revision.available_commands, "declare_risk"),
  );
  const shown = readDetail(at, readRisk(at.address));
  const options = Promise.all([declare, shown]).then(([offer, read]) =>
    offer?.is_available === true ||
    (["update", "review"] as const).some(
      (command) => findOffer(read?.risk.available_commands ?? [], command)?.is_available === true,
    )
      ? readProvisionOptions(at.revision.projectId, at.revision.revisionId)
      : undefined,
  );
  const [read, risks, coverage, matrix, detail, preferences, query, offer, choices, kept, marked] =
    await Promise.all([
      reading,
      readRisks(at, states, filters, asked),
      readCoverage(at),
      readMatrix(at),
      shown,
      settings,
      asked,
      declare,
      options,
      session,
      readLastMarkedOn(at),
    ]);
  if (read === "not_found") {
    notFound();
  }
  const { estimate, occurred: occurredGrid } = gridsOf(kept?.permissions, at);
  return (
    <>
      <ContextBanner reading={read} />
      {/* The filter, the grid and the links compose the changes they make to the address. */}
      <PendingAddress>
        <Screen density={FUNCTION_DENSITY.risks} fillWide>
          <RisksHeader
            count={risks.kind === "read" ? risks.page.total : 0}
            actions={
              <IdentifyRisk
                projectId={at.revision.projectId}
                offer={offer}
                options={choices}
                estimate={estimate}
              />
            }
          />
          <MockupNotice lists />
          <div className="flex flex-wrap items-end justify-between gap-x-8 gap-y-3">
            <FiguresGrid className="min-w-0 grow basis-[40rem]">
              {risks.kind === "read" ? <ProvisionSummary totals={risks.totals} /> : null}
              <RiskCoverageSummary coverage={coverage} context={coverage.context} />
            </FiguresGrid>
          </div>
          <RiskMatrixSection
            reading={read}
            matrix={matrix}
            computedAt={coverage.context.computed_at}
            folded={kept?.display_preferences?.charts?.risk_matrix?.folded ?? true}
          />
          {/* The detail of a risk, beside the grid, keeps the height to read it in: the window too
              low for the chart, the grid and the detail scrolls the page. */}
          <div
            className={`flex flex-col gap-4 lg:flex-1 lg:flex-row ${detail === undefined ? "lg:min-h-0" : "lg:min-h-96"}`}
          >
            <div className="flex min-w-0 flex-col gap-2 lg:min-h-0 lg:flex-1">
              <RisksBlock
                risks={risks}
                query={query}
                preferences={preferences}
                originGrid={occurredGrid}
                states={states}
                filters={filters}
                lastMarkedOn={marked}
                panel={
                  <RiskFilterPanel
                    states={states}
                    filters={filters}
                    fields={refusedFields(risks)}
                  />
                }
              />
            </div>
            {detail === undefined ? null : (
              <aside className="flex shrink-0 flex-col gap-4 lg:w-96 lg:overflow-y-auto">
                <RiskDetail {...detail} projectId={at.revision.projectId} options={choices} />
              </aside>
            )}
          </div>
        </Screen>
      </PendingAddress>
    </>
  );
}
