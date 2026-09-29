// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the grid of the planning that are more than a value formatted (WF-PLA-0080): the
 * scheduling mode and the progress of a task, each an icon named for its value; its duration
 * and its total float in days; the critical path marked on the float by an icon and bold type,
 * never by a colour alone (WF-PLA-0100); and its predecessors, named by their row numbers with
 * the type of each link and its lag, as Microsoft Project writes them.
 *
 * Everything shown is what the API gives: the mode, the progress, the float and the critical
 * path are read from the task, never deduced from its dates. A predecessor is named by the row
 * number the API gave its node in the same answer.
 */
"use client";

import { Circle, CircleCheck, Contrast, Flame, type LucideIcon, PenLine, Zap } from "lucide-react";
import { useTranslations } from "next-intl";
import { createContext, useContext } from "react";

import type { components } from "@/api/generated/schema";

import type { Node } from "./nodes";

/** The scheduling mode of a task (WF-PLA-0020). */
type SchedulingMode = components["schemas"]["SchedulingMode"];

/** The progress of a task (WF-PLA-0130). */
type TaskProgress = components["schemas"]["TaskProgress"];

/** A link of a task to one of its predecessors (WF-PLA-0030). */
type Predecessor = components["schemas"]["Predecessor"];

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

/**
 * The row numbers of the answer the grid shows, by node: how a predecessor is named. The grid
 * of the planning provides them; none, and no predecessor is found.
 */
export const RowNumbers = createContext<ReadonlyMap<string, number>>(new Map());

/** Render the scheduling mode of a task, an icon named for it; nothing for a line. */
export function SchedulingModeCell({ node }: { readonly node: Node }) {
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

/** Render the progress of a task, an icon named for it; nothing for a line. */
export function ProgressCell({ node }: { readonly node: Node }) {
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

/** Render a number of days with its unit, in the language of the interface. */
export function DaysCell({ days }: { readonly days: number | null | undefined }) {
  const t = useTranslations("planningGrid");
  return days === null || days === undefined ? null : t("days", { days });
}

/**
 * Render the total float of a task, in days — none for a task in manual mode, which bears no
 * float (WF-PLA-0100) —, and, on the critical path, the icon that names it before the float set
 * in bold: the mark reads without its colour.
 */
export function FloatCell({ node }: { readonly node: Node }) {
  const t = useTranslations("planningGrid");
  const task = node.task;
  if (task?.is_critical !== true) {
    return <DaysCell days={task?.total_float_days} />;
  }
  return (
    <span className="inline-flex items-center gap-1 font-semibold text-foreground">
      <Flame role="img" aria-label={t("critical")} className="size-3 shrink-0">
        <title>{t("critical")}</title>
      </Flame>
      <DaysCell days={task.total_float_days} />
    </span>
  );
}

/** The direction of the lag of a link: a lag, a lead, or none. */
function direction(lag: number): "lag" | "lead" | "none" {
  if (lag > 0) {
    return "lag";
  }
  return lag < 0 ? "lead" : "none";
}

/**
 * The type of a link as its name shows it: none for the plain link, finish to start without a
 * lag, which the row number alone says.
 */
function shownLink({ link_type, lag_days }: Predecessor): string {
  return link_type === "finish_to_start" && lag_days === 0 ? "none" : link_type;
}

/**
 * Render the predecessors of a task as Microsoft Project writes them, each named by its row
 * number, then by the type of its link and its lag unless it is plain: `4;3DD+5 j`, `2FD-2 j`.
 * A predecessor the answer does not hold — outside what a search retained — has no number to
 * show, and says so.
 */
export function PredecessorsCell({ node }: { readonly node: Node }) {
  const t = useTranslations("planningGrid");
  const rows = useContext(RowNumbers);
  const name = (predecessor: Predecessor) =>
    t("predecessor", {
      row: rows.get(predecessor.predecessor_node_id)?.toString() ?? t("unknownRow"),
      link: shownLink(predecessor),
      direction: direction(predecessor.lag_days),
      lag: predecessor.lag_days,
    });
  return (node.predecessors ?? []).map(name).join(t("predecessorSeparator"));
}
