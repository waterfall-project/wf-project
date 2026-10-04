// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The actual costs of a project (WF-CRE-0040, US-0230), at the route of their function
 * (`functions.json`): the banner of the reading context (WF-IHM-0020); the total of the tracked
 * scope, the total excluded and the general total of the lines retained, and the date of the last
 * import (WF-CRE-0050); the filters by scope, sub-project and period; the grid of a page of the
 * lines, sorted, filtered and paged by the server as the address asks (`sort_by`,
 * `in_tracked_scope`, `subproject_id`, `from`, `to`, `offset`, under the names of the contract);
 * and the journal of the imports, a page of it. The actual costs belong to the project, not to a
 * revision: the revision of the route is the reading context of the banner alone. Every figure as
 * the API gives it: the front computes, sorts, filters and pages nothing. A read the API refuses,
 * or cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { readProjectContext } from "@/components/context/reading";
import {
  type CostFilters,
  COSTS_PAGE,
  IMPORTS_PAGE,
  readCostFilters,
  readPage,
  scopeParameter,
} from "@/components/costs/address";
import { CostFilterBar } from "@/components/costs/cost-filters";
import {
  COST_GRID,
  COST_SORT_COLUMNS,
  costRow,
  type CostSortColumn,
} from "@/components/costs/cost-grid";
import { ListPages } from "@/components/costs/cost-pages";
import { CostSummary } from "@/components/costs/cost-totals";
import { CostsGrid } from "@/components/costs/costs-grid";
import { ImportJournal } from "@/components/costs/import-journal";
import { PendingAddress } from "@/components/grid/pending-address";
import { type GridQuery, readGridQuery } from "@/components/grid/query";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import type { PageSearchParams } from "@/navigation/context";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../../../../title";
import { type GridAddress, gridAddress } from "../grid-screen";
import type { RevisionParams } from "../page";

/** The lines of the journal a page holds: an import a month, a year and some. */
const IMPORTS_LIMIT = 12;

/** Title the tab with the function, and with the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<RevisionParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functions.actualCosts", projectId);
}

/**
 * A page of the actual costs as the address asks it — sorted, filtered, from its place — and the
 * totals of every line retained; of each line, the fields the grid reads alone (`costRow`).
 */
async function readCosts(
  { revision, address, context }: GridAddress,
  filters: CostFilters,
  asked: Promise<GridQuery<CostSortColumn>>,
) {
  const { sort } = await asked;
  const subproject = context.parameters.get("subproject_id");
  const scope = scopeParameter(filters.scope);
  const offset = readPage(address, COSTS_PAGE);
  const answer = await readOrFail("listActualCosts", () =>
    serverClient().GET("/projects/{project_id}/actual-costs", {
      params: {
        path: { project_id: revision.projectId },
        query: {
          ...(offset === 0 ? {} : { offset }),
          ...(subproject === null ? {} : { subproject_id: subproject }),
          ...(filters.from === undefined ? {} : { from: filters.from }),
          ...(filters.to === undefined ? {} : { to: filters.to }),
          ...(scope === undefined ? {} : { in_tracked_scope: scope }),
          ...(sort === undefined ? {} : { sort_by: sort.column, sort_order: sort.order }),
        },
      },
    }),
  );
  return {
    costs: { items: answer.items.map(costRow), totals: answer.totals },
    lastImport: answer.last_import_at,
    page: answer.meta,
  };
}

/** A page of the journal of the imports, from the place the address asks. */
async function readImports({ revision, address }: GridAddress) {
  const offset = readPage(address, IMPORTS_PAGE);
  return readOrFail("listCostImports", () =>
    serverClient().GET("/projects/{project_id}/cost-imports", {
      params: {
        path: { project_id: revision.projectId },
        query: { limit: IMPORTS_LIMIT, ...(offset === 0 ? {} : { offset }) },
      },
    }),
  );
}

/** The sub-projects of the project, which the filter offers. */
async function readSubprojects({ revision }: GridAddress) {
  const subprojects = await readOrFail("listSubprojects", () =>
    serverClient().GET("/projects/{project_id}/subprojects", {
      params: { path: { project_id: revision.projectId } },
    }),
  );
  return subprojects.map(({ subproject_id, code, label }) => ({ id: subproject_id, code, label }));
}

/** The title of the screen, and how many lines the filters retain. */
function CostsHeader({ count }: { readonly count: number }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.actualCosts")}
      icon={FUNCTION_ICONS.actual_costs}
      density={FUNCTION_DENSITY.actual_costs}
      subtitle={t("actualCosts.summary", { count })}
    />
  );
}

/** Render the actual costs of a project: their totals, their filters, their grid, their imports. */
export default async function ActualCostsPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "actual-costs");
  const filters = readCostFilters(at.address);
  const settings = requestSession().then(
    (session) => session?.user.display_preferences?.grids?.[COST_GRID.key] ?? undefined,
  );
  const asked = settings.then((kept) => readGridQuery(at.address, COST_SORT_COLUMNS, kept?.sort));
  const [reading, costs, imports, subprojects, preferences, query] = await Promise.all([
    readProjectContext(at.pathname, at.context),
    readCosts(at, filters, asked),
    readImports(at),
    readSubprojects(at),
    settings,
    asked,
  ]);
  if (reading === "not_found") {
    notFound();
  }
  return (
    <>
      <ContextBanner reading={reading} />
      {/* The filters, the grid and the pages compose the changes they make to the address. */}
      <PendingAddress>
        <Screen density={FUNCTION_DENSITY.actual_costs} fill>
          <CostsHeader count={costs.page.total} />
          <CostSummary totals={costs.costs.totals} lastImport={costs.lastImport} />
          <CostFilterBar
            filters={filters}
            subproject={at.context.parameters.get("subproject_id") ?? undefined}
            subprojects={subprojects}
          />
          <div className="flex min-h-0 flex-1 flex-col gap-4 lg:flex-row">
            <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2">
              <CostsGrid costs={costs.costs} query={query} preferences={preferences} />
              <ListPages list="costs" page={costs.page} shown={costs.costs.items.length} />
            </div>
            <aside className="flex shrink-0 flex-col gap-4 lg:w-[28rem] lg:overflow-y-auto">
              <ImportJournal imports={imports.items} page={imports.meta} />
            </aside>
          </div>
        </Screen>
      </PendingAddress>
    </>
  );
}
