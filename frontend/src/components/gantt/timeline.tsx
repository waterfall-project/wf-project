// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a timeline reads of its tasks (FBS-4.3.1, WF-PLA-0140), which its page reads on the server
 * and its frieze draws in the browser (`timeline-chart.tsx`): a module without a directive, so that
 * both sides read it.
 *
 * The server selects the tasks of a timeline (`listNodes`, `timeline_id`, #463), in the order of
 * the plan and without their ancestors. The screen applies the same criterion to the answer once
 * more (`inscribedTo`) — a temporary gap of EP-02: the fake back ignores the filters of
 * `listNodes`, and the mock-up must stay right against it; against a server that applies them, it
 * changes nothing. It goes with the back of EP-03.
 */
import type { components } from "@/api/generated/schema";

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
