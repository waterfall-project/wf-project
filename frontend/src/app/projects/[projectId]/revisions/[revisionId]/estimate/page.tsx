// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The estimate of a revision (WF-DEV-0050, WF-DEV-0060, US-0220), at the route of its function
 * (`functions.json`): the banner of its reading context (WF-IHM-0020); the hourly rates its
 * calculation lacks and its indicators (`EstimateSummary`), read for the sub-project the address
 * filters; and the grid on the main structure of the revision, its tasks and their lines, asked
 * and handed the fields it shows alone (`grid-screen.ts`). The rows come in the order of the answer, with the
 * totals of the answer: a header clicked or a search entered changes the address, and this page
 * reads anew (`grid-screen.ts`). The
 * indicators and the rates are read alongside the grid, and so are the categories and the roles
 * the lines are named by and chosen from (US-0120). The grid is entered from the keyboard, and takes
 * a block pasted from a spreadsheet, when the revision lists `edit_estimate` available to the caller
 * (WF-IHM-0040, WF-IHM-0050). Its head leads to the workload of the project, a leaf of the estimate
 * with a screen of its own (FBS-4.4.4), in the same context. A refused read of the rates
 * or of the reference data is thrown for the pages of the shell to say, as the grid's; indicators
 * refused as expected are said unavailable, the rest of the screen shown: the screen never shows
 * a figure it did not read.
 */
import { ChartColumnStacked } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { readOrFail, readUnlessRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { EstimateSummary } from "@/components/estimate/estimate-summary";
import {
  ESTIMATE_FIELDS,
  ESTIMATE_GRID,
  ESTIMATE_SORT_COLUMNS,
  type EstimateReference,
} from "@/components/grid/estimate";
import { EstimateGrid } from "@/components/grid/estimate-grid";
import type { NodeTotals } from "@/components/grid/nodes";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import type { PageSearchParams } from "@/navigation/context";
import { functionHref, leafOf } from "@/navigation/functions";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../../../../title";
import { type GridAddress, gridAddress, readGridScreen } from "../grid-screen";
import type { RevisionParams } from "../page";

/** Title the tab with the function, and with the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<RevisionParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functions.estimate", projectId);
}

/**
 * The refusals of the indicators the screen does without: not found, or refused for a missing
 * hourly rate — what #159 foresaw while the contract did not say it.
 */
const INDICATOR_REFUSALS = [
  { status: 404 },
  { status: 409, code: "HOURLY_RATE_MISSING" },
  { status: 422, code: "HOURLY_RATE_MISSING" },
] as const;

/**
 * The indicators of the estimate of the revision, for the sub-project the address filters —
 * the whole project otherwise —; none when the API refuses them as expected, not found or for
 * a missing hourly rate: the rest of the screen stays, and says the indicators unavailable,
 * rather than coming down. Any other answer follows the rule of the reads (`readUnlessRefused`).
 */
async function readIndicators({ revision, context }: GridAddress) {
  const subproject = context.parameters.get("subproject_id");
  return readUnlessRefused("getEstimateIndicators", INDICATOR_REFUSALS, () =>
    serverClient().GET("/projects/{project_id}/estimate-indicators", {
      params: {
        path: { project_id: revision.projectId },
        query: {
          revision_id: revision.revisionId,
          ...(subproject === null ? {} : { scope: subproject }),
        },
      },
    }),
  );
}

/**
 * The indicators of the estimate of the revision, if the API gives them, and the hourly rates
 * its calculation lacks, which the screen cannot do without.
 */
async function readEstimateFigures(at: GridAddress) {
  const { revision } = at;
  const client = serverClient();
  const path = { project_id: revision.projectId };
  return Promise.all([
    readIndicators(at),
    readOrFail("getMissingRates", () =>
      client.GET("/projects/{project_id}/estimate-indicators/missing-rates", {
        params: { path, query: { revision_id: revision.revisionId } },
      }),
    ),
  ]);
}

/**
 * A list of the reference data the screen can do without: `undefined` when the API does not find
 * it or refuses it — the roles are the reference's (`resource_settings`), which an estimator may
 * not read —, the rest of the screen shown. Any other answer follows the rule of the reads: the
 * API out of reach, a failure of the service, a lost session are thrown for the shell to say.
 */
async function readOptional<T>(
  operation: string,
  call: () => Promise<{ data?: T; error?: unknown; response: Response }>,
): Promise<T | undefined> {
  return readUnlessRefused(operation, [{ status: 404 }, { status: 403 }], call);
}

/**
 * The categories and the roles the lines of the estimate are named by, as the grid reads them —
 * an identifier, a name, whether it may still be chosen, nothing more crossing to the browser.
 * The deactivated ones are read too: a line may bear one, which it shows; the list of a cell
 * offers the active ones alone (WF-REF-0150). A list the API refuses is none: its column is
 * neither named nor entered, and the screen stays.
 */
async function readReference(): Promise<EstimateReference> {
  const client = serverClient();
  const query = { include_inactive: true };
  const [categories, roles] = await Promise.all([
    readOptional("listCostCategories", () =>
      client.GET("/reference/cost-categories", { params: { query } }),
    ),
    readOptional("listResourceRoles", () =>
      client.GET("/reference/resource-roles", { params: { query } }),
    ),
  ]);
  return {
    categories: categories?.map((category) => ({
      id: category.cost_category_id,
      label: category.label,
      active: category.is_active,
    })),
    roles: roles?.map((role) => ({
      id: role.resource_role_id,
      label: role.label,
      active: role.is_active,
    })),
  };
}

/** The workload of the project, a leaf of the estimate with a screen of its own (FBS-4.4.4). */
const WORKLOAD = leafOf("FBS-4.4.4");

/**
 * The title of the grid, and what it holds: the structure, its tasks and lines retained; and the
 * link to the workload of the project, in the same context.
 */
function EstimateHeader({
  label,
  totals,
  workload,
}: {
  readonly label: string;
  readonly totals: NodeTotals;
  readonly workload: string | undefined;
}) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.estimate")}
      icon={FUNCTION_ICONS.estimate}
      density={FUNCTION_DENSITY.estimate}
      subtitle={t("estimateGrid.summary", {
        structure: label,
        tasks: totals.task_count,
        lines: totals.estimate_line_count,
      })}
      actions={
        workload === undefined ? undefined : (
          <Link href={workload} className={buttonVariants({ variant: "outline", size: "sm" })}>
            <ChartColumnStacked aria-hidden="true" />
            {t(WORKLOAD.label)}
          </Link>
        )
      }
    />
  );
}

/** Render the estimate of a revision: what its calculation lacks, its indicators, its grid. */
export default async function EstimatePage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "estimate");
  const [screen, [indicators, missingRates], reference, session] = await Promise.all([
    readGridScreen(at, {
      key: ESTIMATE_GRID.key,
      sortable: ESTIMATE_SORT_COLUMNS,
      fields: ESTIMATE_FIELDS,
    }),
    readEstimateFigures(at),
    readReference(),
    requestSession(),
  ]);
  return (
    <>
      <ContextBanner reading={screen.reading} />
      <Screen density={FUNCTION_DENSITY.estimate} fill>
        <EstimateHeader
          label={screen.label}
          totals={screen.nodes.totals}
          workload={functionHref(WORKLOAD, at.context)}
        />
        <EstimateSummary
          indicators={indicators}
          missingRates={missingRates}
          permissions={session?.permissions ?? []}
        />
        <EstimateGrid
          nodes={screen.nodes}
          structure={screen.structure}
          structureVersion={screen.structureVersion}
          filters={screen.filters}
          reference={reference}
          editable={screen.reading.edits.has("edit_estimate")}
          tasksEditable={screen.reading.edits.has("edit_planning")}
          query={screen.query}
          preferences={screen.preferences}
        />
      </Screen>
    </>
  );
}
