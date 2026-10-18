// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The gestures on the work breakdown of a project (EP-14/L44c), each made on its reading whole and
 * sent whole (`setWorkBreakdown`, decision of EP-02/L42f): an element added under its parent, last
 * among its siblings, without an identifier — the server gives it one (WF-DAT-0060) —; an element
 * renamed; an element deleted, with what it holds. The marks of the reading (`is_match`) are not
 * written. The pointer of an element in what is sent says, of a refusal by field, which element it
 * is about (`elementAt`).
 *
 * Neither server nor client: the commands of the grid read it in the browser.
 */
import type { components } from "@/api/generated/schema";

import type { BreakdownKind, BreakdownRow, WorkBreakdown } from "./settings-grids";

/** The work breakdown as `setWorkBreakdown` writes it. */
export type BreakdownWrite = components["schemas"]["WorkBreakdown"];

/** An order item as `setWorkBreakdown` writes it. */
type OrderItem = components["schemas"]["OrderItem"];

/** A gesture on the work breakdown: add under a row — or an order item —, rename, delete. */
export type Gesture =
  | { readonly kind: "add"; readonly parent: BreakdownRow | undefined }
  | { readonly kind: "rename"; readonly row: BreakdownRow }
  | { readonly kind: "delete"; readonly row: BreakdownRow };

/** An element of what is sent: its kind, its pointer, what it is, and how it changes. */
interface Slot {
  readonly id: string | undefined;
  readonly kind: BreakdownKind;
  readonly pointer: string;
  readonly element: { label: string };
  /** Add an element under it, last; the pointer of the element added. None under a deliverable. */
  readonly add?: (label: string) => string;
  readonly remove: () => void;
}

/** The work breakdown of a reading as `setWorkBreakdown` writes it: each element, without its mark. */
function written(reading: WorkBreakdown): OrderItem[] {
  return reading.order_items.map(({ order_item_id, label, work_packages }) => ({
    order_item_id,
    label,
    work_packages: work_packages.map(({ work_package_id, label, deliverables }) => ({
      work_package_id,
      label,
      deliverables: deliverables.map(({ deliverable_id, label }) => ({ deliverable_id, label })),
    })),
  }));
}

/** Each element of what is sent, in the order entered, with its pointer. */
function slots(items: OrderItem[]): Slot[] {
  return items.flatMap((item, i): Slot[] => {
    const at = `/order_items/${String(i)}`;
    return [
      {
        id: item.order_item_id,
        kind: "order_item",
        pointer: at,
        element: item,
        add: (label) =>
          `${at}/work_packages/${String(item.work_packages.push({ label, deliverables: [] }) - 1)}`,
        remove: () => items.splice(i, 1),
      },
      ...item.work_packages.flatMap((pack, j): Slot[] => {
        const under = `${at}/work_packages/${String(j)}`;
        return [
          {
            id: pack.work_package_id,
            kind: "work_package",
            pointer: under,
            element: pack,
            add: (label) =>
              `${under}/deliverables/${String(pack.deliverables.push({ label }) - 1)}`,
            remove: () => item.work_packages.splice(j, 1),
          },
          ...pack.deliverables.map((deliverable, k): Slot => ({
            id: deliverable.deliverable_id,
            kind: "deliverable",
            pointer: `${under}/deliverables/${String(k)}`,
            element: deliverable,
            remove: () => pack.deliverables.splice(k, 1),
          })),
        ];
      }),
    ];
  });
}

/**
 * The work breakdown to send for a gesture made on a reading whole, from its counter, and the
 * pointer of the element added or renamed; none for a deletion, or for an element the reading no
 * longer holds.
 */
export function edited(
  from: WorkBreakdown,
  counter: number,
  gesture: Gesture,
  label: string,
): { readonly sent: BreakdownWrite; readonly at: string | undefined } {
  const items = written(from);
  const find = (row: BreakdownRow) => slots(items).find((slot) => slot.id === row.id);
  let at: string | undefined;
  if (gesture.kind === "add") {
    at =
      gesture.parent === undefined
        ? `/order_items/${String(items.push({ label, work_packages: [] }) - 1)}`
        : find(gesture.parent)?.add?.(label);
  } else if (gesture.kind === "rename") {
    const slot = find(gesture.row);
    if (slot !== undefined) {
      slot.element.label = label;
      at = slot.pointer;
    }
  } else {
    find(gesture.row)?.remove();
  }
  return { sent: { order_items: items, lock_version: counter }, at };
}

/**
 * The element of what was sent a refusal by field points at — the deepest one whose pointer starts
 * it: `/order_items/0/work_packages/1/label` is the second work package of the first order item —,
 * by its kind, its label and its pointer; none for a field of no element (`/lock_version`).
 */
export function elementAt(
  sent: BreakdownWrite,
  pointer: string,
): { readonly kind: BreakdownKind; readonly label: string; readonly pointer: string } | undefined {
  const holding = slots(sent.order_items).filter((slot) => pointer.startsWith(`${slot.pointer}/`));
  const deepest = holding.at(-1);
  return deepest === undefined
    ? undefined
    : { kind: deepest.kind, label: deepest.element.label, pointer: deepest.pointer };
}
