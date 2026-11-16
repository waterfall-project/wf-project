// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The detail of the workload by role and by task (WF-DEV-0090, US-2040), in its card under the
 * chart: the grid of the plan the chart reads, on the same basis and under the same node of
 * organisation, with no choice of its own. A task leads, for a session that reads the planning, to
 * the planning grid of the revision the basis reads (`context.revision_id`) — the revision under way,
 * the reference, the marked revision chosen —, in the context of the screen, the task named
 * (`onTask`), which the grid shows and aims at. A server component: it hands the grid data only.
 */
import { Rows3 } from "lucide-react";
import { useTranslations } from "next-intl";

import { onTask } from "@/components/grid/planning-target";
import type { GridPreferences } from "@/components/grid/settings";
import { SectionCard } from "@/components/shell/section-card";
import type { ProjectContext } from "@/navigation/context";
import { functionHref, functionOf } from "@/navigation/functions";

import { workloadDetail } from "./detail-rows";
import type { WorkloadPlan } from "./workload-chart";
import { WorkloadDetailGrid } from "./workload-detail";

/**
 * The address of the planning grid of the revision a plan reads, in the context of the screen —
 * its filters, never the structure it may name —; none for a session that does not read the
 * planning.
 */
export function planningOf(
  plan: WorkloadPlan,
  context: ProjectContext,
  permissions: readonly string[] | undefined,
): string | undefined {
  return permissions?.includes("planning.read") === true
    ? functionHref(functionOf("planning"), {
        ...context,
        revisionId: plan.context.revision_id,
        revisionInPath: true,
        structure: undefined,
      })
    : undefined;
}

/** Render the card of the detail of a plan. */
export function WorkloadDetailSection({
  workload,
  planning,
  preferences,
}: {
  readonly workload: WorkloadPlan;
  /** The address of the planning grid of the revision read; none, the tasks lead nowhere. */
  readonly planning: string | undefined;
  /** The settings the account keeps for the grid of the detail, if any. */
  readonly preferences: GridPreferences | undefined;
}) {
  const t = useTranslations("workload");
  const detail = workloadDetail(workload, (task) =>
    planning === undefined ? undefined : onTask(planning, task.node_id),
  );
  return (
    <SectionCard title={t("detailTitle")} icon={Rows3}>
      <WorkloadDetailGrid
        detail={detail}
        revision={workload.context.revision_id}
        preferences={preferences}
      />
    </SectionCard>
  );
}
