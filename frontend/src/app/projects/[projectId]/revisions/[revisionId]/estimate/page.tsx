// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The estimate of a revision (WF-DEV-0050, WF-DEV-0060, US-0220), at the route of its function
 * (`functions.json`): the banner of its reading context (WF-IHM-0020); the hourly rates its
 * calculation lacks and its indicators (`EstimateSummary`), read for the sub-project the address
 * filters; and the grid on the main structure of the revision, its tasks and their lines. The
 * rows come in the order of the answer, with the totals of the answer: a header clicked or a
 * search entered changes the address, and this page reads anew (`grid-screen.ts`). The
 * indicators and the rates are read alongside the grid. A refused read of the rates is thrown
 * for the pages of the shell to say, as the grid's; indicators refused as expected are said
 * unavailable, the rest of the screen shown: the screen never shows a figure it did not read.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { Unreachable } from "@/api/client";
import { isGatewayFailure, readOrFail, refusalOf } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { EstimateSummary } from "@/components/estimate/estimate-summary";
import { ESTIMATE_GRID, ESTIMATE_SORT_COLUMNS } from "@/components/grid/estimate";
import { EstimateGrid } from "@/components/grid/estimate-grid";
import type { NodeList } from "@/components/grid/nodes";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import type { PageSearchParams } from "@/navigation/context";
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

/** The statuses of the refusal #159 foresees for indicators while hourly rates are missing. */
const RATE_REFUSALS: ReadonlySet<number> = new Set([409, 422]);

/**
 * Whether the API refuses the indicators as the screen expects it may: not found, or refused
 * for a missing hourly rate — what the contract does not say yet (#159).
 */
function isExpectedRefusal(status: number, body: unknown): boolean {
  if (status === 404) {
    return true;
  }
  return (
    RATE_REFUSALS.has(status) &&
    typeof body === "object" &&
    body !== null &&
    "code" in body &&
    body.code === "HOURLY_RATE_MISSING"
  );
}

/**
 * The indicators of the estimate of the revision, for the sub-project the address filters —
 * the whole project otherwise —; none when the API refuses them as expected, not found or for
 * a missing hourly rate: the rest of the screen stays, and says the indicators unavailable,
 * rather than coming down. Any other answer follows the rule of the reads (`readOrFail`): a
 * failure of the service is thrown with its correlation identifier, a refusal for want of a
 * session leads to the sign-in, a gateway saying the service is down is the API out of reach.
 */
async function readIndicators({ revision, context }: GridAddress) {
  const subproject = context.parameters.get("subproject_id");
  const answer = await serverClient().GET("/projects/{project_id}/estimate-indicators", {
    params: {
      path: { project_id: revision.projectId },
      query: {
        revision_id: revision.revisionId,
        ...(subproject === null ? {} : { scope: subproject }),
      },
    },
  });
  const { ok, status } = answer.response;
  if (ok) {
    return answer.data;
  }
  if (isExpectedRefusal(status, answer.error)) {
    return undefined;
  }
  if (isGatewayFailure(answer.response, answer.error)) {
    throw new Unreachable();
  }
  throw refusalOf("getEstimateIndicators", status, answer.error);
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

/** The title of the grid, and what it holds: the structure, its tasks and lines retained. */
function EstimateHeader({ label, nodes }: { readonly label: string; readonly nodes: NodeList }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.estimate")}
      icon={FUNCTION_ICONS.estimate}
      density={FUNCTION_DENSITY.estimate}
      subtitle={t("estimateGrid.summary", {
        structure: label,
        tasks: nodes.totals.task_count,
        lines: nodes.totals.estimate_line_count,
      })}
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
  const [screen, [indicators, missingRates], session] = await Promise.all([
    readGridScreen(at, { key: ESTIMATE_GRID.key, sortable: ESTIMATE_SORT_COLUMNS }),
    readEstimateFigures(at),
    requestSession(),
  ]);
  return (
    <>
      <ContextBanner reading={screen.reading} />
      <Screen density={FUNCTION_DENSITY.estimate} fill>
        <EstimateHeader label={screen.label} nodes={screen.nodes} />
        <EstimateSummary
          indicators={indicators}
          missingRates={missingRates}
          permissions={session?.permissions ?? []}
        />
        <EstimateGrid nodes={screen.nodes} query={screen.query} preferences={screen.preferences} />
      </Screen>
    </>
  );
}
