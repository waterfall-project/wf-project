// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A timeline drawn (FBS-4.3.1, WF-PLA-0140): the tasks and the milestones inscribed to it, each a
 * row — its number, its label, its dates as the API gives them — and its bar on the one axis of
 * time the rows share, drawn as the Gantt draws it (`GanttCell`), the three sorts of task apart
 * and the critical path told by the drawing and by the name of the bar. Read, never entered.
 *
 * The server selects the tasks of a timeline (`listNodes`, `timeline_id`, #463), in the order of
 * the plan and without their ancestors. The screen applies the same criterion to the answer once
 * more (`inscribedTo`) — a temporary gap of EP-02: the fake back ignores the filters of
 * `listNodes`, and the mock-up must stay right against it; against a server that applies them, it
 * changes nothing. It goes with the back of EP-03.
 */
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { formatPlanningDate } from "@/i18n/format";

import { GanttAxis, GanttCell, GanttRows } from "./gantt";
import type { GanttRow } from "./layout";

/** An inscription of a task: to a timeline, or to the time/time tracking. */
type TrackingEntry = components["schemas"]["TrackingEntry"];

/** A task as a timeline reads it: its number, its label, its dates, its inscriptions. */
export interface TimelineTask extends GanttRow {
  readonly row_number: number;
  readonly task?:
    | (NonNullable<GanttRow["task"]> & {
        readonly label: string;
        readonly tracking?: readonly TrackingEntry[];
      })
    | null;
}

/**
 * The tasks of an answer inscribed to a timeline, in the order of the answer: what a server that
 * applies `timeline_id` renders, kept once more against one that does not (the fake back of EP-02).
 */
export function inscribedTo<Task extends TimelineTask>(
  tasks: readonly Task[],
  timeline: string,
): Task[] {
  return tasks.filter((node) =>
    (node.task?.tracking ?? []).some(
      (entry) => entry.kind === "timeline" && entry.timeline_id === timeline,
    ),
  );
}

/** The width of the drawing, in pixels: its axis is written at it. */
const DRAWING = 480;

/** Render the tasks of a timeline, each with its bar on the axis they share. */
export function TimelineTable({
  name,
  tasks,
}: {
  readonly name: string;
  readonly tasks: readonly TimelineTask[];
}) {
  const t = useTranslations();
  const locale = useLocale();
  const date = (instant: { readonly date: string } | null | undefined) =>
    instant === null || instant === undefined
      ? ""
      : formatPlanningDate(instant.date, locale, "short");
  return (
    <GanttRows rows={tasks}>
      <Table
        aria-label={name}
        container={{ className: "w-fit max-w-full rounded-md border" }}
        className="text-xs tabular-nums"
      >
        <TableHeader>
          <TableRow>
            <TableHead scope="col" className="h-8 text-right">
              {t("grid.columns.rowNumber")}
            </TableHead>
            <TableHead scope="col">{t("grid.columns.label")}</TableHead>
            <TableHead scope="col">{t("grid.columns.startDate")}</TableHead>
            <TableHead scope="col">{t("grid.columns.finishDate")}</TableHead>
            <TableHead scope="col" className="relative" style={{ width: DRAWING }}>
              <span className="sr-only">{t("grid.columns.gantt")}</span>
              <GanttAxis width={DRAWING - 16} />
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {tasks.map((node) => (
            <TableRow key={node.node_id} className="h-7">
              <TableCell className="text-right text-muted-foreground">{node.row_number}</TableCell>
              <TableCell>{node.task?.label}</TableCell>
              <TableCell>{date(node.task?.start)}</TableCell>
              <TableCell>{date(node.task?.finish)}</TableCell>
              <TableCell>
                <GanttCell row={node} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </GanttRows>
  );
}
