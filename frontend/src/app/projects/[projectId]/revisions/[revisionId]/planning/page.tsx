// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the planning of a revision (WF-PLA-0080, US-0220), at the route of its function
 * (`functions.json`): the banner of its reading context (WF-IHM-0020), which names the structure
 * read and offers the others of the revision, and the grid on the structure the address names — the
 * main one by default, a differential, the own estimate of a risk (US-0500) —, mounted anew for
 * each (#819.3), its tasks alone — the server renders no line for it (`kinds`) —, asked and handed
 * the fields it shows alone (`grid-screen.ts`). The rows come in the order of the answer, with the
 * totals of the answer: a header clicked or a search entered changes the address, and this page
 * reads anew (`grid-screen.ts`). The Gantt is the last column of the grid, row for row (FBS-4.3.3).
 * Its head leads to the leaves of the planning with a screen of their own — the timelines
 * (FBS-4.3.1), the imports and exports of the project (FBS-4.3.4), the task tree (FBS-4.3.5) —, in
 * the same context.
 *
 * On a differential, « Écarts seulement » (`DifferencesOnly`, US-0700) is written in the address,
 * said in the banner, and the server retains the nodes whose difference is added, removed or
 * modified.
 *
 * The grid is filtered by a lot or a post of the work breakdown of the project, read whole, above
 * it (`BreakdownFilterChoice`): the server retains the subtree of the task that bears it and its
 * ancestors, and the banner shows the filter active; the filter is not offered when the API refuses
 * the work breakdown. Where the revision lists `edit_planning` available, the attachment of a task
 * is entered in its column, chosen among the same posts and lots (WF-PLA-0170), and the screen
 * cannot do without the work breakdown; in the empty grid of the main structure, the skeleton is
 * offered as the revision lists `generate_skeleton` (WF-PRJ-0030) — never on a differential nor on
 * the own estimate of a risk, which the skeleton, generated on the main structure, would not fill.
 * The timelines of the project (`listTimelines`) name the inscriptions of its tasks, in a column
 * hidden until shown, and are the boxes of the submenu « Chronologies » of the menu of their cells
 * (US-0480). The Gantt reads the hours of a day of the installation (`getDurationUnits`), which
 * graduate its finest level, and is exported with the date its dates were calculated at
 * (`meta.scheduled_at`). A task the address names (`task`, `planning-target.ts`) — the detail of
 * the workload leads there — is unfolded down to and aimed at once the grid is hydrated. The
 * screen is served (US-1470): it shows what the service renders — dates, margins, critical path and
 * conflicts — and writes it back, with no note of the mock-up.
 */
import type { Metadata } from "next";
import Link from "next/link";
import { useTranslations } from "next-intl";

import { readOrFail, readUnlessRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { findOffer } from "@/components/commands/offer";
import { ContextBanner } from "@/components/context/context-banner";
import { breakdownChip } from "@/components/grid/breakdown-filter";
import { TreeFilters } from "@/components/grid/tree-filters";
import { originNames } from "@/components/grid/origin-filter";
import type { NodeTotals } from "@/components/grid/nodes";
import { PendingAddress } from "@/components/grid/pending-address";
import {
  PLANNING_FIELDS,
  PLANNING_GRID,
  PLANNING_KINDS,
  PLANNING_SORT_COLUMNS,
} from "@/components/grid/planning";
import type { ProjectReading } from "@/components/context/reading";
import { hoursOfDay } from "@/components/gantt/scale";
import { PlanningGrid, type PlanningGridProps } from "@/components/grid/planning-grid";
import { targetTask } from "@/components/grid/planning-target";
import type { ChoiceOption } from "@/components/grid/row-choices";
import { OwnEstimateScope } from "@/components/revisions/own-estimate-scope";
import { StructureCommands } from "@/components/revisions/structure-commands";
import { FUNCTION_DENSITY, FUNCTION_ICONS, LEAF_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import type { PageSearchParams, ProjectContext } from "@/navigation/context";
import { functionHref, leafOf } from "@/navigation/functions";

import { screenMetadata } from "../../../../../title";
import { gridAddress, provenanceOf, readGridScreen } from "../grid-screen";
import type { RevisionParams } from "../page";
import { GridCard } from "@/components/shell/grid-card";

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
  { leaf: leafOf("FBS-4.3.1"), Icon: LEAF_ICONS["FBS-4.3.1"], help: "timelines" },
  { leaf: leafOf("FBS-4.3.4"), Icon: LEAF_ICONS["FBS-4.3.4"], help: "exchanges" },
  { leaf: leafOf("FBS-4.3.5"), Icon: LEAF_ICONS["FBS-4.3.5"], help: "taskTree" },
] as const;

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
          {LEAVES.map(({ leaf, Icon, help }) => {
            const href = functionHref(leaf, context);
            return href === undefined ? null : (
              <CommandTooltip
                key={leaf.code}
                label={t(leaf.label)}
                help={t(`commands.${help}.help`)}
              >
                <Link href={href} className={buttonVariants({ variant: "outline", size: "sm" })}>
                  <Icon aria-hidden="true" />
                  {t(leaf.label)}
                </Link>
              </CommandTooltip>
            );
          })}
        </div>
      }
    />
  );
}

/**
 * The timelines of the project, by their identifier and their label, which name the inscriptions of
 * the tasks and are offered by the menu of their cells (US-0480); none when the API does not find
 * the timelines of the project, the grid then naming none and offering no submenu.
 */
async function readTimelines(projectId: string): Promise<readonly ChoiceOption[] | undefined> {
  const timelines = await readUnlessRefused("listTimelines", [{ status: 404 }], () =>
    serverClient().GET("/projects/{project_id}/timelines", {
      params: { path: { project_id: projectId } },
    }),
  );
  return timelines?.map((timeline) => ({ id: timeline.timeline_id, label: timeline.label }));
}

/**
 * The grid of the planning and its Gantt, which zooms down to the hours of a day of the installation
 * and names the project, the revision and the date of calculation in its exported image.
 */
function PlanningWithGantt({
  grid,
  reading,
  scheduledAt,
  hoursPerDay,
}: {
  readonly grid: Omit<PlanningGridProps, "gantt">;
  readonly reading: ProjectReading;
  readonly scheduledAt: string;
  readonly hoursPerDay: string;
}) {
  const t = useTranslations("contextBanner");
  return (
    <PlanningGrid
      {...grid}
      gantt={{
        hoursPerDay: hoursOfDay(hoursPerDay),
        exported: { provenance: provenanceOf(reading, t("currentRevision")), scheduledAt },
      }}
    />
  );
}

/** Render the grid of the planning on the structure of a revision the address names. */
export default async function PlanningPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const at = gridAddress(revision, search, "planning");
  const [screen, timelines, units] = await Promise.all([
    readGridScreen(at, {
      key: PLANNING_GRID.key,
      sortable: PLANNING_SORT_COLUMNS,
      kinds: PLANNING_KINDS,
      fields: PLANNING_FIELDS,
      byBreakdown: true,
      byDifference: true,
      byOrigin: true,
      // The attachment of a task is chosen among the lots and the posts where it is entered.
      needsBreakdown: (reading) => reading.edits.has("edit_planning"),
      chooses: true,
    }),
    readTimelines(revision.projectId),
    readOrFail("getDurationUnits", () => serverClient().GET("/reference/duration-units")),
  ]);
  // An own estimate in arrears is entered all the same: its first entry updates it (US-3140).
  const editable = screen.commands.has("edit_planning") || screen.gated.has("edit_planning");
  const skeleton =
    screen.kind === "main"
      ? findOffer(screen.reading.revision?.available_commands ?? [], "generate_skeleton")
      : undefined;
  // One address asked for the whole screen: the structure chosen in the banner and a sort or a filter
  // of the grid compose, whichever comes first (défaut n° 20 de `typescript.md`).
  return (
    <PendingAddress>
      <ContextBanner
        reading={screen.reading}
        structure={screen.structures}
        base={screen.base}
        breakdown={breakdownChip(screen.breakdownFilter, screen.breakdown?.items)}
        difference={screen.difference}
      />
      <Screen density={FUNCTION_DENSITY.planning} fill>
        <PlanningHeader label={screen.label} totals={screen.nodes.totals} context={at.context} />
        <StructureCommands
          structure={screen.structures?.read}
          version={screen.structureVersion}
          commands={screen.commands}
          mergeOffer={findOffer(
            screen.reading.revision?.available_commands ?? [],
            "merge_structure",
          )}
          revision={revision}
        />
        <OwnEstimateScope
          structure={screen.read}
          commands={screen.commands}
          gated={screen.gated}
          revision={revision}
        >
          <GridCard fill>
            <PlanningWithGantt
              key={screen.structure.structure_id}
              reading={screen.reading}
              scheduledAt={screen.scheduledAt}
              hoursPerDay={units.hours_per_day}
              grid={{
                nodes: screen.nodes,
                structure: screen.structure,
                structureVersion: screen.structureVersion,
                planningStart: { on: screen.planningStart, label: screen.label },
                filters: screen.filters,
                query: screen.query,
                preferences: screen.preferences,
                undoable: editable,
                editable,
                differential: screen.kind !== "main",
                comparing: screen.base?.chosen !== undefined,
                origins: originNames(screen.origin),
                treeFilters: (
                  <TreeFilters
                    breakdown={screen.breakdown}
                    difference={screen.difference}
                    differential={screen.kind !== "main"}
                    origin={screen.origin}
                  />
                ),
                // The attachment is chosen among the same items, where the planning may be entered.
                breakdown: editable ? screen.breakdown?.items : undefined,
                skeleton,
                timelines,
                timelineCreation: findOffer(
                  screen.reading.project.available_commands,
                  "manage_timelines",
                ),
                // The task a link leads to — from the detail of the workload —, shown and aimed at.
                target: targetTask(at.address),
              }}
            />
          </GridCard>
        </OwnEstimateScope>
      </Screen>
    </PendingAddress>
  );
}
