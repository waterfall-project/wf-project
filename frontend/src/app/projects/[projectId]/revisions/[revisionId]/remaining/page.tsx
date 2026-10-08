// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The remaining to commit of a revision (FBS-4.5, WF-RAE-0020, WF-RAE-0040, US-0230), at the route
 * of its function (`functions.json`): the banner of its reading context (WF-IHM-0020), which shows
 * the one filter its reads take — the sub-project, by which the nodes are read, said to restrict
 * the grid alone (#459): the indicators take the revision alone (`getRemainingIndicators`), and no
 * date —; the indicators of the remaining to commit (`RemainingSummary`); and the grid on the
 * main structure of the revision, its tasks and their lines, asked and handed the fields it shows
 * alone (`grid-screen.ts`), the lines of the tasks started alone unless the address asks the tasks
 * not started too (`progress`), which a link of its head offers. The grid is entered from the keyboard, and places undo and
 * redo, when the revision lists `edit_remaining` available to the caller (US-0140). Its head leads
 * to the Kanban of the start of the tasks, a leaf with a screen of its own (FBS-4.5.3), in the
 * same context. Indicators the API does not find are said unavailable, the rest of the screen
 * shown; any other refusal follows the rule of the reads.
 */
import type { Metadata } from "next";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { readUnlessRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import type { NodeTotals } from "@/components/grid/nodes";
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

/** The filter of the screen its indicators do not take: the sub-project restricts the grid alone. */
const GRID_ONLY = ["subproject_id"] as const;

/** The Kanban of the start of the tasks, a leaf of the remaining to commit (FBS-4.5.3). */
const KANBAN = leafOf("FBS-4.5.3");

/** The icon of the Kanban, which its own screen shows too. */
const KanbanIcon = LEAF_ICONS["FBS-4.5.3"];

/**
 * The title of the grid, and what it holds: the structure, its tasks and lines retained; the link
 * that shows the tasks not started too, or the tasks started alone; and the link to the Kanban.
 */
function RemainingHeader({
  label,
  totals,
  notStarted,
  progress,
  kanban,
}: {
  readonly label: string;
  readonly totals: NodeTotals;
  readonly notStarted: boolean;
  readonly progress: string;
  readonly kanban: string | undefined;
}) {
  const t = useTranslations();
  const action = buttonVariants({ variant: "outline", size: "sm" });
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
          <Link href={progress} className={action}>
            {notStarted ? t("remainingGrid.startedOnly") : t("remainingGrid.showNotStarted")}
          </Link>
          {kanban === undefined ? null : (
            <Link href={kanban} className={action}>
              <KanbanIcon aria-hidden="true" />
              {t(KANBAN.label)}
            </Link>
          )}
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
  const [screen, indicators] = await Promise.all([
    readGridScreen(at, {
      key: REMAINING_GRID.key,
      sortable: REMAINING_SORT_COLUMNS,
      fields: REMAINING_FIELDS,
      progress: [...progress],
    }),
    readIndicators(at),
  ]);
  const notStarted = progress.includes("not_started");
  return (
    <>
      <ContextBanner reading={screen.reading} gridOnly={GRID_ONLY} />
      <Screen density={FUNCTION_DENSITY.remaining} fill>
        <RemainingHeader
          label={screen.label}
          totals={screen.nodes.totals}
          notStarted={notStarted}
          progress={progressHref(at.pathname, searchQuery(search), !notStarted)}
          kanban={functionHref(KANBAN, at.context)}
        />
        <RemainingSummary indicators={indicators} />
        <RemainingGrid
          nodes={screen.nodes}
          structure={screen.structure}
          filters={screen.filters}
          editable={screen.reading.edits.has("edit_remaining")}
          query={screen.query}
          preferences={screen.preferences}
        />
      </Screen>
    </>
  );
}
