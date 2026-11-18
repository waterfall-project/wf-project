// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The spending projection of a project (FBS-4.4.5, WF-DEV-0100, US-2050), at the route of its leaf
 * of the estimate (`functions.json`), which the screens of the estimate and of the remaining to
 * commit lead to: the banner of the reading context (WF-IHM-0020); the spending by cost type and by
 * month as the API computes it (`getProjectSpending`) on the basis, the marked revision, the date
 * (consumption, or payment) and the sub-project the address asks — the server filters, the front
 * computes nothing —, in a stacked chart whose values are read in a table and exported as a PNG
 * image (WF-IHM-0130); under it, the same projection in a tree grid from the cost type to the
 * category, a column for each month, read only (`SpendingGrid`). The choice offers the bases the
 * project admits, the marked revisions of the project — every one of them, whatever the server
 * pages (`readEveryPage`, #303) — and its sub-projects (`listSubprojects`).
 *
 * A projection the API refuses is said unavailable, and why, the rest of the screen shown. Any other
 * answer follows the rule of the reads (`readOrFail`).
 */
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { readEveryPage } from "@/api/every-page";
import { readOrFail, readOrRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import {
  askSubprojects,
  type ProjectReading,
  readProjectContext,
} from "@/components/context/reading";
import { LEAF_DENSITY, LEAF_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { SectionCard } from "@/components/shell/section-card";
import { SPENDING_GRID_KEY, spendingDetail } from "@/components/spending/spending-rows";
import { SpendingGrid } from "@/components/spending/spending-grid";
import {
  PAYMENT_DELAYS,
  SPENDING_REFUSED,
  SPENDING_REVISION,
  type SpendingAddress,
  type SpendingAsked,
  type SpendingBasis,
  type SpendingRead,
  SpendingSection,
} from "@/components/spending/spending-section";
import type { PageSearchParams, SearchParameters } from "@/navigation/context";
import { requestSession } from "@/session/request";
import { Rows3 } from "lucide-react";

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
  return screenMetadata("functions.spending", projectId);
}

/** A revision of the project, as the API reads it. */
type Revision = components["schemas"]["Revision"];

/** The bases of a projection, as the contract names them. */
const BASES: readonly SpendingBasis[] = [
  "reference_budget",
  "marked_remaining",
  "current_remaining",
];

/** A parameter of the address, `undefined` when it is absent or empty. */
function given(address: SearchParameters, name: string): string | undefined {
  const value = address.get(name);
  return value === null || value === "" ? undefined : value;
}

/**
 * What the address asks of the projection: its basis — the remaining of the revision under way
 * unless it names another —, the marked revision of that basis, the date of payment, the
 * sub-project.
 */
function spendingAsked(address: SearchParameters): SpendingAsked {
  const named = address.get("basis");
  return {
    basis: BASES.find((basis) => basis === named) ?? "current_remaining",
    revision: given(address, SPENDING_REVISION),
    subproject: given(address, "subproject_id"),
    payment: address.get(PAYMENT_DELAYS) === "true",
  };
}

/**
 * The projection on what the address asks — the marked revision sent only with the basis that takes
 * it, the sub-project and the payment delays the server applies —; the sub-projects and the marked
 * revisions of the project, which the choice offers.
 */
async function readSpending({ revision }: GridAddress, asked: SpendingAsked) {
  const client = serverClient();
  const path = { project_id: revision.projectId };
  const query = {
    basis: asked.basis,
    ...(asked.basis === "marked_remaining" && asked.revision !== undefined
      ? { revision_id: asked.revision }
      : {}),
    ...(asked.payment ? { payment_delays: true } : {}),
    ...(asked.subproject === undefined ? {} : { subproject_id: asked.subproject }),
  };
  const [spending, subprojects, marked, session] = await Promise.all([
    readOrRefused("getProjectSpending", SPENDING_REFUSED, () =>
      client.GET("/projects/{project_id}/spending", { params: { path, query } }),
    ),
    readOrFail("listSubprojects", () => askSubprojects(revision.projectId)),
    readEveryPage("listRevisions", (page) =>
      client.GET("/projects/{project_id}/revisions", {
        params: { path, query: { status: ["marked"], ...page } },
      }),
    ),
    requestSession(),
  ]);
  return {
    spending: spending satisfies SpendingRead,
    subprojects,
    marked,
    preferences: session?.display_preferences?.grids?.[SPENDING_GRID_KEY] ?? undefined,
  };
}

/**
 * The bases the project admits (WF-DEV-0100): the budget of the reference, only with a reference
 * revision; the remaining of a marked revision, only when the project has one; the revision under
 * way, always — alone on a project with neither.
 */
function offeredBases(reading: ProjectReading, marked: readonly Revision[]): SpendingBasis[] {
  return [
    ...(reading.project.reference_revision_id === null ? [] : (["reference_budget"] as const)),
    ...(marked.length === 0 ? [] : (["marked_remaining"] as const)),
    "current_remaining",
  ];
}

/** The parameters of the address as Next hands them, the first value of each. */
function parametersOf(search: PageSearchParams): SpendingAddress["parameters"] {
  return Object.entries(search).flatMap(([name, value]) => {
    const first = typeof value === "string" ? value : value?.[0];
    return first === undefined ? [] : [[name, first] as const];
  });
}

/** The head of the screen, its projection, and the grid of the projection the API computed. */
function SpendingScreen({
  reading,
  read,
  asked,
  address,
}: {
  readonly reading: ProjectReading;
  readonly read: Awaited<ReturnType<typeof readSpending>>;
  readonly asked: SpendingAsked;
  readonly address: SpendingAddress;
}) {
  const t = useTranslations();
  const { project } = reading;
  return (
    <Screen density={LEAF_DENSITY["FBS-4.4.5"]}>
      <PageHeader
        title={t("functions.spending")}
        icon={LEAF_ICONS["FBS-4.4.5"]}
        density={LEAF_DENSITY["FBS-4.4.5"]}
      />
      <SpendingSection
        spending={read.spending}
        asked={asked}
        bases={offeredBases(reading, read.marked)}
        marked={read.marked}
        subprojects={read.subprojects}
        address={address}
        project={{ label: project.label, code: project.code ?? project.project_id }}
        shown={reading.revision}
      />
      {read.spending.kind === "refused" ? null : (
        <SectionCard title={t("spending.gridTitle")} icon={Rows3}>
          <SpendingGrid
            detail={spendingDetail(read.spending.data)}
            revision={read.spending.data.context.revision_id}
            preferences={read.preferences}
          />
        </SectionCard>
      )}
    </Screen>
  );
}

/** Render the spending projection of a project. */
export default async function SpendingPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "spending");
  const asked = spendingAsked(at.address);
  const [reading, read] = await Promise.all([
    // The projection takes the sub-project, which the banner shows, and no date: the figure is
    // dated by its own calculation (#302).
    readProjectContext(at.pathname, at.context, ["subproject_id"]),
    readSpending(at, asked),
  ]);
  if (reading === "not_found") {
    notFound();
  }
  return (
    <>
      <ContextBanner reading={reading} />
      <SpendingScreen
        reading={reading}
        read={read}
        asked={asked}
        address={{ pathname: at.pathname, parameters: parametersOf(search) }}
      />
    </>
  );
}
