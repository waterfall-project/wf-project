// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the planning of a revision (WF-PLA-0080, US-0220), at the route of its function
 * (`functions.json`): the banner of its reading context (WF-IHM-0020), and the grid on the main
 * structure of the revision, its tasks alone — the server renders no line for it (`kinds`) —,
 * asked and handed the fields it shows alone (`fields`, `projectNodes`). The rows come in the order of the answer,
 * with the totals of the answer: a header clicked or a search entered changes the address, and
 * this page reads anew (`grid-screen.ts`).
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { ContextBanner } from "@/components/context/context-banner";
import { type NodeList, nodeFieldNames, projectNodes } from "@/components/grid/nodes";
import {
  PLANNING_FIELDS,
  PLANNING_GRID,
  PLANNING_KINDS,
  PLANNING_SORT_COLUMNS,
} from "@/components/grid/planning";
import { PlanningGrid } from "@/components/grid/planning-grid";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import type { PageSearchParams } from "@/navigation/context";

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

/** The title of the grid, and what it holds: the structure, and its tasks retained. */
function PlanningHeader({ label, nodes }: { readonly label: string; readonly nodes: NodeList }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.planning")}
      icon={FUNCTION_ICONS.planning}
      density={FUNCTION_DENSITY.planning}
      subtitle={t("planningGrid.summary", { structure: label, tasks: nodes.totals.task_count })}
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
  const screen = await readGridScreen(gridAddress(revision, search, "planning"), {
    key: PLANNING_GRID.key,
    sortable: PLANNING_SORT_COLUMNS,
    kinds: PLANNING_KINDS,
    fields: nodeFieldNames(PLANNING_FIELDS),
  });
  return (
    <>
      <ContextBanner reading={screen.reading} />
      <Screen density={FUNCTION_DENSITY.planning} fill>
        <PlanningHeader label={screen.label} nodes={screen.nodes} />
        <PlanningGrid
          nodes={projectNodes(screen.nodes, PLANNING_FIELDS)}
          structure={screen.structure}
          query={screen.query}
          preferences={screen.preferences}
        />
      </Screen>
    </>
  );
}
