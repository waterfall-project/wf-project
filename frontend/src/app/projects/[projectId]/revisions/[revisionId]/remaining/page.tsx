// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The remaining to commit of a revision (FBS-4.5, WF-RAE-0020, WF-RAE-0040, US-0230), at the route
 * of its function (`functions.json`): the banner of its reading context (WF-IHM-0020), which shows
 * the one filter its reads take — the sub-project, by which the nodes are read, said to restrict
 * the grid alone (#459): the indicators take the revision alone (`getRemainingIndicators`), and no
 * date —; the indicators of the remaining to commit (`RemainingSummary`); and the grid on the main
 * structure of the revision, its tasks and their lines, asked and handed the fields it shows alone
 * (`grid-screen.ts`), the lines of the tasks started alone unless the address asks the tasks not
 * started too (`progress`), which a link of its head offers, and filtered by a lot or a post of the
 * work breakdown read whole, above it, as the estimate's (WF-RAE-0040). The grid is entered from
 * the keyboard, its tasks and its lines created and deleted, and places undo and redo, when the
 * structure lists `edit_remaining` available to the caller (US-0140, WF-RAE-0040): before the
 * project is in progress it lists it unavailable, and the grid is read only. The categories a line
 * is created from, and the sub-projects its lines are carried to (US-0480), are read then. Its head
 * leads to the Kanban of the start of the tasks, a leaf with a screen of its own (FBS-4.5.3), in the
 * same context, and, when the project lists the import of a remaining to commit, to the imports and
 * exports, where it is exercised (#521). Indicators the API does not find are said unavailable, the
 * rest of the screen shown; any other refusal follows the rule of the reads.
 */
import type { Metadata } from "next";
import Link from "next/link";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { readEveryPageUnlessRefused } from "@/api/every-page";
import { readUnlessRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { ContextBanner, type Restrictions } from "@/components/context/context-banner";
import { askSubprojects } from "@/components/context/reading";
import { ExchangesLink } from "@/components/exchanges/exchanges-link";
import { breakdownChip } from "@/components/grid/breakdown-filter";
import { BreakdownFilterChoice } from "@/components/grid/breakdown-filter-choice";
import type { NodeTotals } from "@/components/grid/nodes";
import { PendingAddress } from "@/components/grid/pending-address";
import {
  REMAINING_FIELDS,
  REMAINING_GRID,
  REMAINING_SORT_COLUMNS,
} from "@/components/grid/remaining";
import { RemainingGrid } from "@/components/grid/remaining-grid";
import { progressHref, readProgress } from "@/components/remaining/address";
import { RemainingSummary } from "@/components/remaining/remaining-summary";
import { FUNCTION_DENSITY, FUNCTION_ICONS, LEAF_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import { type PageSearchParams, searchQuery } from "@/navigation/context";
import { onBasis } from "@/components/workload/workload-basis";
import { functionHref, leafOf } from "@/navigation/functions";

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
  return screenMetadata("functions.remaining", projectId);
}

/**
 * The indicators of the remaining to commit of the revision; none when the API does not find them:
 * the rest of the screen stays, and says them unavailable. Any other answer follows the rule of
 * the reads (`readUnlessRefused`).
 */
async function readIndicators({ revision }: GridAddress) {
  return readUnlessRefused("getRemainingIndicators", [{ status: 404 }], () =>
    serverClient().GET("/projects/{project_id}/remaining-indicators", {
      params: {
        path: { project_id: revision.projectId },
        query: { revision_id: revision.revisionId },
      },
    }),
  );
}

/** The refusals of the optional reads (categories, sub-projects) the screen does without. */
const OPTIONAL_READ_REFUSALS = [{ status: 404 }, { status: 403 }] as const;

/**
 * The categories of cost a line is created from, the active ones — a line created takes an active
 * category (WF-REF-0150) —, as the grid reads them; none when the API refuses the list, and the grid
 * then creates no line.
 */
async function readCategories() {
  const categories = await readEveryPageUnlessRefused(
    "listCostCategories",
    OPTIONAL_READ_REFUSALS,
    (page) => serverClient().GET("/reference/cost-categories", { params: { query: { ...page } } }),
  );
  return categories?.map((category) => ({
    id: category.cost_category_id,
    label: category.label,
    active: category.is_active,
  }));
}

/**
 * The sub-projects of the project, which the menu of the cells of a line offers it (US-0480); none
 * when the API refuses the list, and the grid then offers no submenu.
 */
async function readSubprojects(projectId: string) {
  // The one answer the banner reads too, once per request.
  const subprojects = await readUnlessRefused("listSubprojects", OPTIONAL_READ_REFUSALS, () =>
    askSubprojects(projectId),
  );
  return subprojects?.map((subproject) => ({
    id: subproject.subproject_id,
    label: subproject.label,
    code: subproject.code,
  }));
}

/**
 * The filters of the screen its indicators do not take: the sub-project, the lot and the post
 * restrict the grid alone.
 */
const RESTRICTS: Restrictions = {
  subproject_id: "grid",
  work_package_id: "grid",
  order_item_id: "grid",
};

/** The Kanban of the start of the tasks, a leaf of the remaining to commit (FBS-4.5.3). */
const KANBAN = leafOf("FBS-4.5.3");

/** The icon of the Kanban, which its own screen shows too. */
const KanbanIcon = LEAF_ICONS["FBS-4.5.3"];

/** The workload of the project (FBS-4.4.4): the remaining to commit is what it is computed on here. */
const WORKLOAD = leafOf("FBS-4.4.4");

/** The icon of the workload, which its own screen shows too. */
const WorkloadIcon = LEAF_ICONS["FBS-4.4.4"];

/**
 * The title of the grid, and what it holds: the structure, its tasks and lines retained; the link
 * that shows the tasks not started too, or the tasks started alone; the links to the Kanban and to
 * the workload, opened on the remaining of the revision under way (#1069); and,
 * when the project lists the import of a remaining to commit, the link to the imports and exports.
 */
function RemainingHeader({
  label,
  totals,
  notStarted,
  progress,
  kanban,
  workload,
  exchanges,
}: {
  readonly label: string;
  readonly totals: NodeTotals;
  readonly notStarted: boolean;
  readonly progress: string;
  readonly kanban: string | undefined;
  readonly workload: string | undefined;
  readonly exchanges: ReactNode;
}) {
  const t = useTranslations();
  const action = buttonVariants({ variant: "outline", size: "sm" });
  const shown = notStarted ? t("remainingGrid.startedOnly") : t("remainingGrid.showNotStarted");
  return (
    <PageHeader
      title={t("functions.remaining")}
      icon={FUNCTION_ICONS.remaining}
      density={FUNCTION_DENSITY.remaining}
      subtitle={t("estimateGrid.summary", {
        structure: label,
        tasks: totals.task_count,
        lines: totals.estimate_line_count,
      })}
      actions={
        <>
          <CommandTooltip label={shown} help={t("commands.startedOnly.help")}>
            <Link href={progress} className={action}>
              {shown}
            </Link>
          </CommandTooltip>
          {kanban === undefined ? null : (
            <CommandTooltip label={t(KANBAN.label)} help={t("commands.kanban.help")}>
              <Link href={kanban} className={action}>
                <KanbanIcon aria-hidden="true" />
                {t(KANBAN.label)}
              </Link>
            </CommandTooltip>
          )}
          {workload === undefined ? null : (
            // An icon alone, named for the readers of the screen, and by its tooltip for the pointer:
            // the title, the subtitle and four links with their words leave the title no room on a
            // window of 1280 points, and the totals of the grid out of it.
            <CommandTooltip label={t(WORKLOAD.label)} help={t("commands.workload.help")}>
              <Link
                href={workload}
                aria-label={t(WORKLOAD.label)}
                className={buttonVariants({ variant: "outline", size: "icon" })}
              >
                <WorkloadIcon aria-hidden="true" />
              </Link>
            </CommandTooltip>
          )}
          {exchanges}
        </>
      }
    />
  );
}

/** Render the remaining to commit of a revision: its indicators, its grid. */
export default async function RemainingPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "remaining");
  const progress = readProgress(at.address);
  // The categories are read where the grid is entered alone — it is where a line is created —, as
  // soon as the structure says so, with the indicators still under way.
  const grid = readGridScreen(at, {
    key: REMAINING_GRID.key,
    sortable: REMAINING_SORT_COLUMNS,
    fields: REMAINING_FIELDS,
    progress: [...progress],
    byBreakdown: true,
  }).then(async (read) => {
    const entered = read.commands.has("edit_remaining");
    const [categories, subprojects] = await Promise.all([
      entered ? readCategories() : undefined,
      entered ? readSubprojects(revision.projectId) : undefined,
    ]);
    return { screen: read, categories, subprojects };
  });
  const [{ screen, categories, subprojects }, indicators] = await Promise.all([
    grid,
    readIndicators(at),
  ]);
  const notStarted = progress.includes("not_started");
  const editable = screen.commands.has("edit_remaining");
  return (
    <>
      <ContextBanner
        reading={screen.reading}
        restricts={RESTRICTS}
        breakdown={breakdownChip(screen.breakdownFilter, screen.breakdown?.items)}
      />
      <Screen density={FUNCTION_DENSITY.remaining} fill>
        <RemainingHeader
          label={screen.label}
          totals={screen.nodes.totals}
          notStarted={notStarted}
          progress={progressHref(at.pathname, searchQuery(search), !notStarted)}
          kanban={functionHref(KANBAN, at.context)}
          workload={onBasis(functionHref(WORKLOAD, at.context), "current_remaining")}
          exchanges={
            <ExchangesLink project={screen.reading.project} kind="remaining" context={at.context} />
          }
        />
        <RemainingSummary indicators={indicators} />
        <PendingAddress>
          {screen.breakdown === undefined ? null : (
            <BreakdownFilterChoice choices={screen.breakdown} />
          )}
          <RemainingGrid
            nodes={screen.nodes}
            structure={screen.structure}
            structureVersion={screen.structureVersion}
            filters={screen.filters}
            editable={editable}
            categories={categories}
            subprojects={subprojects}
            query={screen.query}
            preferences={screen.preferences}
          />
        </PendingAddress>
      </Screen>
    </>
  );
}
