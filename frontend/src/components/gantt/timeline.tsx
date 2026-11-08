// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a timeline reads of its tasks (FBS-4.3.1, WF-PLA-0140), which its page reads on the server
 * and its frieze draws in the browser (`timeline-chart.tsx`): a module without a directive, so that
 * both sides read it.
 *
 * The service selects the tasks of a timeline (`listNodes`, `timeline_id`, US-1400), in the order
 * of the plan and without their ancestors; the screen draws them as they come.
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
