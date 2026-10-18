// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the grid of the planning that are more than a value formatted (WF-PLA-0080): the
 * scheduling mode and the progress of a task, each an icon named for its value; its duration in
 * the unit of its entry (WF-PLA-0160) and its total float in working days; the critical path
 * marked on the float by an icon and bold type, never by a colour alone (WF-PLA-0100); and its
 * predecessors, named by their row numbers with the type of each link and its lag in its unit,
 * as Microsoft Project writes them (WF-PLA-0030); the physical progress of a summary, as a
 * percentage, or why it cannot be computed (WF-IND-0060, WF-IND-0010).
 *
 * Everything shown is what the API gives: the mode, the progress, the float and the critical
 * path are read from the task, never deduced from its dates. A predecessor is named by the row
 * number the API gives it in the numbering of the whole structure, whether or not the answer
 * holds it.
 */
"use client";

import { Circle, CircleCheck, Contrast, Flame, type LucideIcon, PenLine, Zap } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { formatDecimal, formatShare } from "@/i18n/format";

import type { PlanningNode } from "./planning";

/** The scheduling mode of a task (WF-PLA-0020). */
type SchedulingMode = components["schemas"]["SchedulingMode"];

/** The progress of a task (WF-PLA-0130). */
type TaskProgress = components["schemas"]["TaskProgress"];

/** A link of a task to one of its predecessors (WF-PLA-0030). */
type Predecessor = components["schemas"]["Predecessor"];

/** A duration in the unit of its entry (WF-PLA-0160). */
type Duration = components["schemas"]["Duration"];

/** A lag in its unit: those of a duration, or a share of the predecessor (WF-PLA-0030). */
type Lag = components["schemas"]["Lag"];

/** An exact decimal of the contract that reads as zero: `0`, `-0`, `0.00`. */
const ZERO = /^-?0+(\.0+)?$/;

/** The icon of each scheduling mode: a mode added without one breaks the typing. */
export const SCHEDULING_MODE_ICONS = {
  automatic: Zap,
  manual: PenLine,
} as const satisfies Readonly<Record<SchedulingMode, LucideIcon>>;

/** The icon of each state of progress: a state added without one breaks the typing. */
export const PROGRESS_ICONS = {
  not_started: Circle,
  started: Contrast,
  completed: CircleCheck,
} as const satisfies Readonly<Record<TaskProgress, LucideIcon>>;

/**
 * The classes of an icon alone in a cell, which bears its name and shows it on hover (`<title>`)
 * to whoever does not read the icon.
 */
const CELL_ICON = "inline size-3.5 text-muted-foreground";

/** Render the scheduling mode of a task, an icon named for it; nothing for a line. */
export function SchedulingModeCell({ node }: { readonly node: PlanningNode }) {
  const t = useTranslations("enums.SchedulingMode");
  const mode = node.task?.scheduling_mode;
  if (mode === undefined) {
    return null;
  }
  const Icon = SCHEDULING_MODE_ICONS[mode];
  return (
    <Icon role="img" aria-label={t(mode)} className={CELL_ICON}>
      <title>{t(mode)}</title>
    </Icon>
  );
}

/**
 * Render the progress of a task, an icon named for it; nothing for a line — in the grid of the
 * planning, as in that of the remaining to commit.
 */
export function ProgressCell({
  node,
}: {
  readonly node: { readonly task?: { readonly progress: TaskProgress } | null };
}) {
  const t = useTranslations("enums.TaskProgress");
  const progress = node.task?.progress;
  if (progress === undefined) {
    return null;
  }
  const Icon = PROGRESS_ICONS[progress];
  return (
    <Icon role="img" aria-label={t(progress)} className={CELL_ICON}>
      <title>{t(progress)}</title>
    </Icon>
  );
}

/**
 * Render a duration as it was entered: its value, formatted as the exact decimal it is, and the
 * suffix of its unit in the language of the interface, as Microsoft Project writes it
 * (WF-PLA-0160).
 */
export function DurationCell({ duration }: { readonly duration: Duration | null | undefined }) {
  const t = useTranslations("planningGrid");
  const units = useTranslations("enums.DurationUnit");
  const locale = useLocale();
  return duration === null || duration === undefined
    ? null
    : t("duration", { value: formatDecimal(duration.value, locale), unit: units(duration.unit) });
}

/**
 * Render the total float of a task, a duration in working days written as a duration is — none
 * for a task in manual mode, which bears no float (WF-PLA-0100) —, and, on the critical path, the
 * icon that names it before the float set in bold: the mark reads without its colour.
 */
export function FloatCell({ node }: { readonly node: PlanningNode }) {
  const t = useTranslations("planningGrid");
  const task = node.task;
  if (task?.is_critical !== true) {
    return <DurationCell duration={task?.total_float} />;
  }
  return (
    <span className="inline-flex items-center gap-1 font-semibold text-foreground">
      <Flame role="img" aria-label={t("critical")} className="size-3 shrink-0">
        <title>{t("critical")}</title>
      </Flame>
      <DurationCell duration={task.total_float} />
    </span>
  );
}

/**
 * Render the physical progress of a summary as a percentage of the exact ratio the API gives; why
 * it cannot be computed when it cannot, said by the catalogue; nothing for a leaf, which bears
 * none (WF-PLA-0080).
 */
export function PhysicalProgressCell({ node }: { readonly node: PlanningNode }) {
  const t = useTranslations();
  const bounds = useTranslations("share");
  const locale = useLocale();
  const progress = node.task?.physical_progress;
  if (progress === undefined || progress === null) {
    return null;
  }
  if (progress.is_computable && progress.value !== undefined && progress.value !== null) {
    return formatShare(progress.value, locale, bounds);
  }
  // Not computable, said as such, and why when the API says it — seen and read with the cell,
  // once: no `title`, which a screen reader would read again as its description (#334).
  const reason = progress.reason ?? null;
  return (
    <span className="truncate text-muted-foreground">
      {t("indicator.notComputable")}
      {reason === null ? null : (
        <span className="text-xs">
          {t("planningGrid.notComputableReason", {
            reason: t(`enums.NotComputableReason.${reason}`),
          })}
        </span>
      )}
    </span>
  );
}

/** The direction of the lag of a link: a lag, a lead, or none — read on the decimal, never a float. */
function direction(lag: Lag): "lag" | "lead" | "none" {
  if (ZERO.test(lag.value)) {
    return "none";
  }
  return lag.value.startsWith("-") ? "lead" : "lag";
}

/**
 * The type of a link as its name shows it: none for the plain link, finish to start without a
 * lag, which the row number alone says.
 */
function shownLink({ link_type, lag }: Predecessor): string {
  return link_type === "finish_to_start" && direction(lag) === "none" ? "none" : link_type;
}

/**
 * Render the predecessors of a task as Microsoft Project writes them, each named by its row
 * number, then by the type of its link and its lag in its unit unless it is plain: `5;4DD+1 sem`,
 * `2FD-2 j`. A predecessor outside what a search retained is named all the same: its number is
 * the one the API gives it.
 */
export function PredecessorsCell({ node }: { readonly node: PlanningNode }) {
  const t = useTranslations("planningGrid");
  const units = useTranslations("enums.LagUnit");
  const locale = useLocale();
  const name = (predecessor: Predecessor) =>
    t("predecessor", {
      row: predecessor.predecessor_row_number.toString(),
      link: shownLink(predecessor),
      direction: direction(predecessor.lag),
      lag: formatDecimal(predecessor.lag.value, locale),
      unit: units(predecessor.lag.unit),
    });
  return (node.predecessors ?? []).map(name).join(t("predecessorSeparator"));
}
