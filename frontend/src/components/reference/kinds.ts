// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the commands and the forms of every list of the reference data share (EP-02/L43): the objects
 * as the server answers a write of them, their kinds, and the objects a form offers to attach one to
 * — among the active ones alone, a deactivated one being no longer offered to an entry (WF-REF-0010),
 * save the one the object is attached to, marked deactivated; named without a mark when the list was
 * not read, its state unknown —, the categories of labour among them (WF-REF-0090).
 *
 * Neither server nor client: the lists and the components of the browser read it alike.
 */
import type { ReferenceKind, ReferenceObject } from "@/api/actions/reference";
import type { components } from "@/api/generated/schema";

export type { ActivationTarget, ReferenceKind, ReferenceObject } from "@/api/actions/reference";

/** The property that identifies an object of each kind, as the contract names it. */
const IDENTIFIER = {
  org_node: "org_node_id",
  resource_role: "resource_role_id",
  calendar: "calendar_id",
  cost_type: "cost_type_id",
  cost_category: "cost_category_id",
} as const satisfies Readonly<Record<ReferenceKind, string>>;

/** The identifier of an object of a kind — a list holds its own kind alone. */
export function idOf(kind: ReferenceKind, object: ReferenceObject): string {
  const id: unknown = (object as Partial<Record<string, unknown>>)[IDENTIFIER[kind]];
  if (typeof id !== "string") {
    throw new Error(`an object of the kind ${kind} has its identifier`);
  }
  return id;
}

/** Whether an object is the one of a kind an identifier names — never throwing on another kind. */
export function isObject(kind: ReferenceKind, object: ReferenceObject, id: string): boolean {
  return (object as Partial<Record<string, unknown>>)[IDENTIFIER[kind]] === id;
}

/** An object a form may attach another to: a node, a category, a calendar, a nature. */
export interface Choice {
  readonly id: string;
  /** Its code, for the objects that have one. */
  readonly code?: string | undefined;
  readonly label: string;
  readonly active: boolean;
  /** Its depth in the tree, for a node of the organisation. */
  readonly level?: number | undefined;
}

/** An object offered to an entry, and whether it is deactivated — the one attached already. */
export interface Offered extends Choice {
  readonly deactivated: boolean;
}

/** The object a form keeps attached to, by the name its row gives it — and its depth, for a node. */
export interface Attached {
  readonly id: string;
  readonly label: string;
  readonly level?: number | undefined;
}

/**
 * The objects offered to an entry, in the order given: the active ones — every one read with
 * `every`, a deactivated one marked —, and the one the object is attached to, by the name its row
 * gives it, marked deactivated when the list read does not offer it. A list not read offers nothing
 * but the one attached, named without a mark: nothing says it is deactivated.
 */
export function offered(
  choices: readonly Choice[] | undefined,
  attached: Attached | undefined,
  every = false,
): Offered[] {
  if (choices === undefined) {
    return attached === undefined ? [] : [{ ...attached, active: false, deactivated: false }];
  }
  const shown = (every ? choices : choices.filter((choice) => choice.active)).map((choice) => ({
    ...choice,
    deactivated: !choice.active,
  }));
  if (attached === undefined || shown.some((choice) => choice.id === attached.id)) {
    return shown;
  }
  const read = choices.find((choice) => choice.id === attached.id);
  return [...shown, { ...read, ...attached, active: false, deactivated: true }];
}

/** A category of cost as a choice: its identifier, its code, its name and its state. */
export function categoryChoice(category: components["schemas"]["CostCategory"]): Choice {
  return {
    id: category.cost_category_id,
    code: category.code,
    label: category.label,
    active: category.is_active,
  };
}

/**
 * The categories of cost a role may be attached to: those whose nature is of labour (WF-REF-0090),
 * as the natures read say — the contract filters the categories by no type of nature (#507); none
 * when either list was not read.
 */
export function labourOf(
  categories: readonly components["schemas"]["CostCategory"][] | undefined,
  natures: readonly components["schemas"]["CostType"][] | undefined,
): Choice[] | undefined {
  if (categories === undefined || natures === undefined) {
    return undefined;
  }
  const labour = new Set(
    natures.filter((nature) => nature.kind === "labor").map((nature) => nature.cost_type_id),
  );
  return categories.filter((category) => labour.has(category.cost_type_id)).map(categoryChoice);
}
