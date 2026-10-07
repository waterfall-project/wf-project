// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The actual costs of a project (WF-CRE-0040, US-0230), at the route of their function
 * (`functions.json`): the banner of the reading context (WF-IHM-0020); the total of the tracked
 * scope, the total excluded and the general total of the lines retained, and the date of the last
 * import (WF-CRE-0050); the filters by scope, sub-project and period; the grid of a page of the
 * lines, sorted, filtered and paged by the server as the address asks (`sort_by`,
 * `in_tracked_scope`, `subproject_id`, `from`, `to`, `offset`, under the names of the contract);
 * and the journal of the imports, a page of it. Its head leads to the imports and exports of the
 * project (FBS-4.3.4), where the actual costs are imported, in the same context. The actual costs
 * belong to the project, not to a revision: the revision of the route is the reading context of
 * the banner alone. Every figure as the API gives it: the front computes, sorts, filters and pages
 * nothing. Filters the API refuses (422) — a period that ends before it starts, a sub-project the
 * project does not have — are said in place of the lines, the filters kept to be changed; any
 * other read the API refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import { readOrFail, readOrRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { askSubprojects, readProjectContext } from "@/components/context/reading";
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
  isKeptSort,
} from "@/components/costs/cost-grid";
import { ListPages } from "@/components/costs/cost-pages";
import { CostSummary } from "@/components/costs/cost-totals";
import { CostsGrid } from "@/components/costs/costs-grid";
import { ImportJournal } from "@/components/costs/import-journal";
import { PendingAddress } from "@/components/grid/pending-address";
import { type GridQuery, readGridQuery } from "@/components/grid/query";
import { FUNCTION_DENSITY, FUNCTION_ICONS, LEAF_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import type { PageSearchParams } from "@/navigation/context";
import { functionHref, leafOf } from "@/navigation/functions";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../../../../title";
import { type GridAddress, gridAddress } from "../grid-screen";
import type { RevisionParams } from "../page";

/** The lines of the journal a page holds: an import a month, a year and some. */
const IMPORTS_LIMIT = 12;

/** The refusal of filters the server cannot apply (`listActualCosts`, 422). */
const FILTERS_REFUSED = [{ status: 422, code: "VALIDATION_FAILED" }] as const;

/** Why the screen reads no line: the key of its sentence in the catalogue. */
type CostsRefusal = "period" | "subproject" | "invalid";

/**
 * Why the API refused the filters, by the parameters its envelope points at (`/query/<name>`): a
 * period that ends before it starts, a sub-project the project does not have; a reason that names
 * none when the envelope points at none of them, or at both.
 */
function costsRefusal(fields: readonly { pointer: string; code: string }[]): CostsRefusal {
  const named = new Set(
    fields.flatMap(({ pointer, code }): CostsRefusal[] => {
      if (pointer === "/query/to" && code === "VALUE_OUT_OF_RANGE") {
        return ["period"];
      }
      return pointer === "/query/subproject_id" ? ["subproject"] : [];
    }),
  );
  const [only] = named;
  return named.size === 1 && only !== undefined ? only : "invalid";
}

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
 * totals and the columns kept from the files of every line retained; of each line, the fields the
 * grid reads alone (`costRow`).
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
  const read = await readOrRefused("listActualCosts", FILTERS_REFUSED, () =>
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
  if (read.kind === "refused") {
    return { refused: costsRefusal(read.problem.fields ?? []) } as const;
  }
  const answer = read.data;
  return {
    costs: {
      items: answer.items.map(costRow),
      totals: answer.totals,
      kept: answer.meta.passthrough_columns,
    },
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

/** The sub-projects of the project, which the filter offers: the answer the banner reads too. */
async function readSubprojects({ revision }: GridAddress) {
  const subprojects = await readOrFail("listSubprojects", () => askSubprojects(revision.projectId));
  return subprojects.map(({ subproject_id, code, label }) => ({ id: subproject_id, code, label }));
}

/**
 * The imports and exports of the project, a leaf of the planning with a screen of its own, where
 * the actual costs are imported (`import_actual_costs`).
 */
const EXCHANGES = leafOf("FBS-4.3.4");

/** The icon of the imports and exports, which their own screen shows too. */
const ExchangesIcon = LEAF_ICONS["FBS-4.3.4"];

/**
 * The title of the screen, and how many lines the filters retain; and the link to the imports and
 * exports of the project, in the same context.
 */
function CostsHeader({
  count,
  exchanges,
}: {
  readonly count: number | undefined;
  readonly exchanges: string | undefined;
}) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.actualCosts")}
      icon={FUNCTION_ICONS.actual_costs}
      density={FUNCTION_DENSITY.actual_costs}
      subtitle={count === undefined ? undefined : t("actualCosts.summary", { count })}
      actions={
        exchanges === undefined ? undefined : (
          <Link href={exchanges} className={buttonVariants({ variant: "outline", size: "sm" })}>
            <ExchangesIcon aria-hidden="true" />
            {t(EXCHANGES.label)}
          </Link>
        )
      }
    />
  );
}

/** Why the screen reads no line, in place of the lines: the filters above stay to be changed. */
function CostsRefused({ reason }: { readonly reason: CostsRefusal }) {
  const t = useTranslations("actualCosts.refused");
  return <p className="text-sm text-muted-foreground">{t(reason)}</p>;
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
  // A column kept from the file sorts by its name, which no list of the screen knows beforehand.
  const asked = settings.then((kept) => {
    const named = [at.address.get("sort_by"), kept?.sort?.column].filter(isKeptSort);
    return readGridQuery(at.address, [...COST_SORT_COLUMNS, ...named], kept?.sort);
  });
  const [reading, costs, imports, subprojects, preferences, query] = await Promise.all([
    // The costs are read for the filtered sub-project alone (`listActualCosts`): no date (#302).
    readProjectContext(at.pathname, at.context, ["subproject_id"]),
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
          <CostsHeader
            count={"refused" in costs ? undefined : costs.page.total}
            exchanges={functionHref(EXCHANGES, at.context)}
          />
          {"refused" in costs ? null : (
            <CostSummary totals={costs.costs.totals} lastImport={costs.lastImport} />
          )}
          <CostFilterBar
            filters={filters}
            subproject={at.context.parameters.get("subproject_id") ?? undefined}
            subprojects={subprojects}
          />
          <div className="flex min-h-0 flex-1 flex-col gap-4 lg:flex-row">
            <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-2">
              {"refused" in costs ? (
                <CostsRefused reason={costs.refused} />
              ) : (
                <>
                  <CostsGrid costs={costs.costs} query={query} preferences={preferences} />
                  <ListPages list="costs" page={costs.page} shown={costs.costs.items.length} />
                </>
              )}
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
