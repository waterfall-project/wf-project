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
import type { Outcome } from "@/api/problem";

/** The work breakdown of a project, as `getWorkBreakdown` reads it. */
export type WorkBreakdownReading = components["schemas"]["WorkBreakdownReading"];

/** What a task may bear of the work breakdown: a post, or a lot. */
export type BreakdownKind = "order_item" | "work_package";

/** A post or a lot a task may bear, by its identifier and its label. */
export interface BreakdownItem {
  readonly id: string;
  readonly label: string;
  readonly kind: BreakdownKind;
}

/**
 * The posts and the lots of a work breakdown read whole, in its order — each post, then its lots —;
 * a deliverable is borne by no task (WF-PLA-0170).
 */
export function breakdownItems(reading: WorkBreakdownReading): BreakdownItem[] {
  return reading.order_items.flatMap((item) => [
    { id: item.order_item_id, label: item.label, kind: "order_item" as const },
    ...item.work_packages.map((work) => ({
      id: work.work_package_id,
      label: work.label,
      kind: "work_package" as const,
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

/**
 * A refusal of the attachment said by the reason of its field: the envelope of a 422 says only that
 * the entry is invalid, its field says why — a post or a lot already borne, the two at once, a
 * structure that bears none, a lot out of the subtree of its post (WF-PLA-0170) —; the parameters of
 * every field are kept, which name the task that bears the item or those the write would move out.
 */
export function byField<T>(outcome: Outcome<T>): Outcome<T> {
  if (outcome.kind === "done" || outcome.kind === "unreachable") {
    return outcome;
  }
  const first = outcome.problem.fields?.[0];
  return outcome.problem.code !== "VALIDATION_FAILED" || first === undefined
    ? outcome
    : { ...outcome, problem: { ...outcome.problem, code: first.code } };
}
