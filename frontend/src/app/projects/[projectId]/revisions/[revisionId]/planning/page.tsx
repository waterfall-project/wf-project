// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the planning of a revision (WF-PLA-0080, US-0220), at the route of its function
 * (`functions.json`): the banner of its reading context (WF-IHM-0020), and the grid on the main
 * structure of the revision, its tasks alone — the server renders no line for it (`kinds`) —,
 * asked and handed the fields it shows alone (`grid-screen.ts`). The rows come in the order of the answer,
 * with the totals of the answer: a header clicked or a search entered changes the address, and
 * this page reads anew (`grid-screen.ts`). The Gantt is the last column of the grid, row for row
 * (FBS-4.3.3). Its head leads to the leaves of the planning with a screen of their own — the
 * timelines (FBS-4.3.1), the imports and exports of the project (FBS-4.3.4), the task tree
 * (FBS-4.3.5) —, in the same context.
 */
import type { Metadata } from "next";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { ContextBanner } from "@/components/context/context-banner";
import type { NodeTotals } from "@/components/grid/nodes";
import {
  PLANNING_FIELDS,
  PLANNING_GRID,
  PLANNING_KINDS,
  PLANNING_SORT_COLUMNS,
} from "@/components/grid/planning";
import { PlanningGrid } from "@/components/grid/planning-grid";
import { FUNCTION_DENSITY, FUNCTION_ICONS, LEAF_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import type { PageSearchParams, ProjectContext } from "@/navigation/context";
import { functionHref, leafOf } from "@/navigation/functions";

import { screenMetadata } from "../../../../../title";
import { gridAddress, readGridScreen } from "../grid-screen";
import type { RevisionParams } from "../page";

/** Title the tab with the function, and with the project. */
export async function generateMetadata({
  params,
}: {
  params: Promise<RevisionParams>;
}): Promise<Metadata> {
  const { projectId } = await params;
  return screenMetadata("functions.planning", projectId);
}

/**
 * The leaves of the planning with a screen of their own, in the order of the FBS, each named by
 * `leafOf`, by which `make screens` knows the page leads to it.
 */
const LEAVES = [
  { leaf: leafOf("FBS-4.3.1"), Icon: LEAF_ICONS["FBS-4.3.1"] },
  { leaf: leafOf("FBS-4.3.4"), Icon: LEAF_ICONS["FBS-4.3.4"] },
  { leaf: leafOf("FBS-4.3.5"), Icon: LEAF_ICONS["FBS-4.3.5"] },
];

/**
 * The title of the grid, and what it holds: the structure, and its tasks retained; and the links to
 * the leaves of the planning, in the same context.
 */
function PlanningHeader({
  label,
  totals,
  context,
}: {
  readonly label: string;
  readonly totals: NodeTotals;
  readonly context: ProjectContext;
}) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.planning")}
      icon={FUNCTION_ICONS.planning}
      density={FUNCTION_DENSITY.planning}
      subtitle={t("planningGrid.summary", { structure: label, tasks: totals.task_count })}
      actions={
        <div className="flex flex-wrap gap-2">
          {LEAVES.map(({ leaf, Icon }) => {
            const href = functionHref(leaf, context);
            return href === undefined ? null : (
              <Link
                key={leaf.code}
                href={href}
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                <Icon aria-hidden="true" />
                {t(leaf.label)}
              </Link>
            );
          })}
        </div>
      }
    />
  );
}

/** Render the grid of the planning on the main structure of a revision. */
export default async function PlanningPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "planning");
  const screen = await readGridScreen(at, {
    key: PLANNING_GRID.key,
    sortable: PLANNING_SORT_COLUMNS,
    kinds: PLANNING_KINDS,
    fields: PLANNING_FIELDS,
  });
  return (
    <>
      <ContextBanner reading={screen.reading} />
      <Screen density={FUNCTION_DENSITY.planning} fill>
        <PlanningHeader label={screen.label} totals={screen.nodes.totals} context={at.context} />
        <PlanningGrid
          nodes={screen.nodes}
          structure={screen.structure}
          query={screen.query}
          preferences={screen.preferences}
          undoable={screen.reading.edits.has("edit_planning")}
        />
      </Screen>
    </>
  );
}
