// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The attachment of a task to the work breakdown in the grid of the planning (WF-PLA-0170,
 * EP-14/L44d): a cell that chooses a post or a lot among the work breakdown read whole, or nothing,
 * written by `updateTaskFacet` — `order_item_id` or `work_package_id`, never both: the field chosen,
 * and the other set to `null` in the same write when the task bears it, the exchange the contract
 * makes in one write (`TaskFacetUpdate`). The cell shows the label the server resolves
 * (`work_breakdown_label`), never one looked up here (WF-ARC-0020).
 *
 * Neither server nor client: the page reads the work breakdown, the grid writes from it.
 */
import type { components } from "@/api/generated/schema";

/** The work breakdown of a project, as `getWorkBreakdown` reads it. */
export type WorkBreakdownReading = components["schemas"]["WorkBreakdownReading"];

/** What a task may bear of the work breakdown: a lot, or a post. */
export type BreakdownKind = "work_package" | "order_item";

/** A lot or a post a task may bear, by its identifier and its label. */
export interface BreakdownItem {
  readonly id: string;
  readonly label: string;
  readonly kind: BreakdownKind;
}

/**
 * The lots and the posts of a work breakdown read whole, in its order — each lot, then its posts —;
 * a deliverable is borne by no task (WF-PLA-0170).
 */
export function breakdownItems(reading: WorkBreakdownReading): BreakdownItem[] {
  return reading.work_packages.flatMap((work) => [
    { id: work.work_package_id, label: work.label, kind: "work_package" as const },
    ...work.order_items.map((item) => ({
      id: item.order_item_id,
      label: item.label,
      kind: "order_item" as const,
    })),
  ]);
}

/** The fields of the attachment a task reads. */
interface Attached {
  readonly order_item_id?: string | null | undefined;
  readonly work_package_id?: string | null | undefined;
}

/** The fields of the task an attachment writes. */
export type AttachmentChange = Pick<
  components["schemas"]["TaskFacetUpdate"],
  "order_item_id" | "work_package_id"
>;

/** What a task bears: the post or the lot, by its identifier; none when it bears nothing. */
export function borne(task: Attached | null | undefined): string | null {
  return task?.order_item_id ?? task?.work_package_id ?? null;
}

/**
 * What a write sends for the item chosen — none, to bear nothing —: the field of its kind, and the
 * other field set to `null` when the task bears it, so that the server never reads both (WF-PLA-0170).
 */
export function attachmentChange(
  task: Attached | null | undefined,
  chosen: BreakdownItem | undefined,
): AttachmentChange {
  const order = task?.order_item_id ?? null;
  const work = task?.work_package_id ?? null;
  if (chosen === undefined) {
    return {
      ...(order === null ? {} : { order_item_id: null }),
      ...(work === null ? {} : { work_package_id: null }),
    };
  }
  return chosen.kind === "order_item"
    ? { order_item_id: chosen.id, ...(work === null ? {} : { work_package_id: null }) }
    : { work_package_id: chosen.id, ...(order === null ? {} : { order_item_id: null }) };
}
