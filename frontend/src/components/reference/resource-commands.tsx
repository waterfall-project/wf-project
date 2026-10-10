// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The forms and the commands of the settings of the resources (FBS-3.2, EP-02/L43b), in dialogs over
 * their lists (`ReferenceForm`), offered to a session that may modify them:
 *
 * - a node of the organisation by its code, unique, its name and its parent — none for a root, sent
 *   null —: a node, active or not, takes place under an active one alone (WF-REF-0070), the parent
 *   it has kept even deactivated; never under itself nor under one of its descendants, which it
 *   takes along;
 * - a resource role by its name, its node, its category of labour and its calendar — the three
 *   attachments required, among the active objects (WF-REF-0090) — and its single capacity, the hours
 *   a month and the headcount they stand for (WF-REF-0100); its node is set at its creation, a role
 *   being recreated under another rather than moved (§3.4.4.2.1): its modification names it, and
 *   leaves it;
 * - a calendar by its name and its seven values of hours, from Monday, and nothing else
 *   (WF-REF-0110).
 *
 * The server judges the rest, each refusal by field said at its field by `ReferenceForm` (EP-14/L42j):
 * a reference unknown (`UNKNOWN_ORG_NODE`, `UNKNOWN_COST_CATEGORY`, `UNKNOWN_CALENDAR`), a node moved
 * under itself or one of its descendants (`ORG_NODE_CYCLE`), a category not of labour
 * (`LABOUR_CATEGORY_REQUIRED`), an attachment deactivated meanwhile (`INACTIVE_REFERENCE_OBJECT`), a
 * figure out of its bounds, with the bound crossed (`VALUE_OUT_OF_RANGE`); a code or a label already
 * held names its holder (`ALREADY_EXISTS`); the version stale (412) is told under the form, with the
 * offer to read the page anew.
 *
 * The designation of the default calendar is that of `calendar-default.tsx`.
 */
"use client";

import { useLocale, useTranslations } from "next-intl";

import { createReferenceObject, updateReferenceObject } from "@/api/actions/reference";
import type { ObjectNames } from "@/components/commands/outcome-notice";
import { editableDecimal } from "@/i18n/format";

import { useListForm } from "./commands";
import { type Choice, offered, type Offered } from "./kinds";
import { treeLabel } from "./org-tree";
import {
  CODE_LENGTH,
  type Draft,
  type FormField,
  LABEL_LENGTH,
  ReferenceForm,
  required,
} from "./reference-form";
import { type Calendar, DAYS, type OrgNode, type ResourceRole } from "./resource-grids";

/** The nodes of the tree, in its order, but a node and its descendants, which follow it deeper. */
function outside(nodes: readonly Choice[], id: string | undefined): Choice[] {
  const at = nodes.findIndex((node) => node.id === id);
  if (at < 0) {
    return [...nodes];
  }
  const level = nodes[at]?.level ?? 0;
  const end = nodes.findIndex((node, index) => index > at && (node.level ?? 0) <= level);
  return [...nodes.slice(0, at), ...(end < 0 ? [] : nodes.slice(end))];
}

/** The parent a node keeps, deactivated, as the tree read or the list shows it, and its own parent. */
interface Kept {
  readonly id: string;
  readonly code?: string | undefined;
  readonly label: string;
  readonly level?: number | undefined;
  /** The node it is under, as the tree read or its row says; none for a root, or when nothing says. */
  readonly above: string | null;
  /** Its place in the tree read; none when the tree does not hold it. */
  readonly place?: number | undefined;
}

/**
 * The deactivated parent a node keeps, by what shows it: the tree read, whose order and depths give
 * its place and the node it is under; or the rows of the list — read under `org_is_active=false`, the
 * tree without the deactivated ones —; or the name the row of the node gives it, and nothing else.
 */
function keptParent(
  { id, label }: { readonly id: string; readonly label: string },
  nodes: readonly Choice[],
  rows: readonly OrgNode[],
): Kept {
  const place = nodes.findIndex((each) => each.id === id);
  const read = nodes[place];
  if (read !== undefined) {
    const depth = read.level ?? 1;
    const above = nodes.slice(0, place).findLast((each) => (each.level ?? 1) < depth);
    const { code, level } = read;
    return { id, code, label: read.label, level, above: above?.id ?? null, place };
  }
  const row = rows.find((each) => each.org_node_id === id);
  return row === undefined
    ? { id, label, above: null }
    : { id, code: row.code, label: row.label, level: row.level, above: row.parent_id ?? null };
}

/**
 * Where a kept parent goes among the parents offered: at its place in the tree read — before the
 * first offer the tree holds after it, the front reordering nothing of what the server orders —; one
 * the tree does not hold, right under its own parent when that one is offered, at the end otherwise.
 */
function slotOf(
  offers: readonly Offered[],
  nodes: readonly Choice[],
  { above, place }: Pick<Kept, "above" | "place">,
): number {
  if (place !== undefined) {
    const after = offers.findIndex(
      (offer) => nodes.findIndex((each) => each.id === offer.id) > place,
    );
    return after < 0 ? offers.length : after;
  }
  const under = above === null ? -1 : offers.findIndex((offer) => offer.id === above);
  return under < 0 ? offers.length : under + 1;
}

/**
 * The parents a node may take (WF-REF-0070): the active nodes of the tree read, in its order — a
 * node, active or not, takes place under an active one alone (`updateOrgNode`, EP-14/L42j) —, never
 * the node itself nor one of its descendants, which it takes along. The parent it has is offered all
 * the same when it is deactivated, marked: the contract refuses a deactivated parent only when the
 * modification changes it, and a node renamed under its deactivated parent keeps it. When the node
 * it is under is offered, or it is a root, it keeps its depth and its place — in the tree read, or
 * under its own parent as the rows of the list name it (`slotOf`); otherwise it comes last, set in by
 * nothing, never seeming to be under a node it is not under nor above one that is not under it.
 */
function parentsOf(
  node: OrgNode | undefined,
  nodes: readonly Choice[],
  rows: readonly OrgNode[],
): Offered[] {
  const offers = outside(nodes, node?.org_node_id)
    .filter((each) => each.active)
    .map((each) => ({ ...each, deactivated: false }));
  const parent = node?.parent_id ?? null;
  if (node === undefined || parent === null || offers.some((offer) => offer.id === parent)) {
    return offers;
  }
  const { above, place, level, ...kept } = keptParent(
    { id: parent, label: node.parent_label ?? "" },
    nodes,
    rows,
  );
  // It keeps its depth, and its place, only when the node it is under is offered — or it is a root.
  const keeps = above === null || offers.some((offer) => offer.id === above);
  const shown: Offered = {
    ...kept,
    level: keeps ? level : undefined,
    active: false,
    deactivated: true,
  };
  const slot = keeps ? slotOf(offers, nodes, { above, place }) : offers.length;
  return [...offers.slice(0, slot), shown, ...offers.slice(slot)];
}

/** Name the objects offered to a choice: a node set in by its depth, a deactivated one marked. */
function useNamed(kind: "org_node" | "cost_category" | "calendar") {
  const t = useTranslations("reference");
  return (choices: readonly Offered[]) =>
    choices.map((choice) => {
      const named =
        choice.code === undefined
          ? choice.label
          : t("codedChoice", { code: choice.code, label: choice.label });
      const shown = choice.deactivated
        ? t("form.deactivatedChoice", { choice: named, kind })
        : named;
      return [choice.id, treeLabel(choice.level ?? 1, shown)] as const;
    });
}

/** The dialog of the list of the organisation, while its form is open. */
export function OrgNodeDialog({
  nodes,
  rows,
}: {
  /** The nodes of the whole tree, in its order, each with its depth and its state. */
  readonly nodes: readonly Choice[];
  /** The nodes the list shows, which name the parent of a node the tree read does not hold. */
  readonly rows: readonly OrgNode[];
}) {
  const t = useTranslations("reference");
  const columns = useTranslations("grid.columns");
  const named = useNamed("org_node");
  const form = useListForm();
  if (form === undefined) {
    return null;
  }
  const { row, ...rest } = form;
  const node = row as OrgNode | undefined;
  // A node takes place under an active one alone, its deactivated parent offered all the same.
  const parents = parentsOf(node, nodes, rows);
  // What names the node that holds a code taken (409 `ALREADY_EXISTS`): the tree, or the list; the
  // label the refusal gives otherwise (`conflicting_object_label`).
  const names = Object.fromEntries(
    [
      ...rows.map((each) => ({ id: each.org_node_id, code: each.code, label: each.label })),
      ...nodes,
    ].map(({ id, code, label }) => [
      id,
      code === undefined ? label : t("codedChoice", { code, label }),
    ]),
  );
  const body = ({ code = "", label = "", parent_id = "" }: Draft) => ({
    code,
    label,
    parent_id: parent_id === "" ? null : parent_id,
  });
  return (
    <ReferenceForm
      {...rest}
      title={node === undefined ? t("orgNodeForm.create") : t("modifyNamed", { name: node.label })}
      hint={t(node === undefined ? "orgNodeForm.createHint" : "orgNodeForm.modifyHint")}
      creating={node === undefined}
      names={names}
      fields={[
        required("code", columns("code"), CODE_LENGTH),
        required("label", columns("label"), LABEL_LENGTH),
        {
          name: "parent_id",
          label: t("orgNodeForm.parent"),
          control: "choice",
          choices: named(parents),
          none: t("orgNodeForm.root"),
        },
      ]}
      initial={
        node === undefined
          ? {}
          : { code: node.code, label: node.label, parent_id: node.parent_id ?? "" }
      }
      ask={(values) =>
        node === undefined
          ? createReferenceObject({ kind: "org_node", body: body(values) })
          : updateReferenceObject(node.org_node_id, {
              kind: "org_node",
              body: { ...body(values), lock_version: node.lock_version },
            })
      }
    />
  );
}

/** The dialog of the list of the roles, while its form is open. */
export function ResourceRoleDialog({
  nodes,
  categories,
  calendars,
}: {
  /** The nodes of the whole tree, in its order, each with its depth and its state. */
  readonly nodes: readonly Choice[];
  /**
   * The categories of cost whose nature is of labour, in the order of the server; none when they
   * were not read, and the category of a role is named as its row names it.
   */
  readonly categories: readonly Choice[] | undefined;
  /** The calendars, in the order of the server. */
  readonly calendars: readonly Choice[];
}) {
  const t = useTranslations("reference");
  const columns = useTranslations("grid.columns");
  const locale = useLocale();
  const nodeNames = useNamed("org_node");
  const categoryNames = useNamed("cost_category");
  const calendarNames = useNamed("calendar");
  const form = useListForm();
  if (form === undefined) {
    return null;
  }
  const { row, ...rest } = form;
  const role = row as ResourceRole | undefined;
  const choice = (
    name: string,
    label: string,
    choices: NonNullable<FormField["choices"]>,
  ): FormField => ({
    name,
    label,
    control: "choice",
    required: true,
    choices,
  });
  const number = (name: string, label: string): FormField => ({
    name,
    label,
    control: "number",
    required: true,
  });
  const attachments = [
    choice(
      "cost_category_id",
      columns("costCategory"),
      categoryNames(
        offered(
          categories,
          role === undefined
            ? undefined
            : { id: role.cost_category_id, label: role.cost_category_label },
        ),
      ),
    ),
    choice(
      "calendar_id",
      columns("calendar"),
      calendarNames(
        offered(
          calendars,
          role === undefined ? undefined : { id: role.calendar_id, label: role.calendar_label },
        ),
      ),
    ),
    number("capacity/monthly_hours", columns("monthlyHours")),
    number("capacity/headcount", columns("headcount")),
  ];
  const written = (values: Draft) => ({
    label: values.label ?? "",
    cost_category_id: values.cost_category_id ?? "",
    calendar_id: values.calendar_id ?? "",
    capacity: {
      monthly_hours: values["capacity/monthly_hours"] ?? "",
      headcount: values["capacity/headcount"] ?? "",
    },
  });
  return (
    <ReferenceForm
      {...rest}
      title={role === undefined ? t("roleForm.create") : t("modifyNamed", { name: role.label })}
      hint={
        role === undefined
          ? t("roleForm.createHint")
          : t("roleForm.modifyHint", { node: role.org_node_label })
      }
      creating={role === undefined}
      fields={[
        required("label", columns("label"), LABEL_LENGTH),
        // The node is set at the creation: a role is recreated under another (§3.4.4.2.1).
        ...(role === undefined
          ? [choice("org_node_id", columns("orgNode"), nodeNames(offered(nodes, undefined)))]
          : []),
        ...attachments,
      ]}
      initial={
        role === undefined
          ? {}
          : {
              label: role.label,
              cost_category_id: role.cost_category_id,
              calendar_id: role.calendar_id,
              "capacity/monthly_hours": editableDecimal(role.capacity.monthly_hours, locale),
              "capacity/headcount": editableDecimal(role.capacity.headcount, locale),
            }
      }
      ask={(values) =>
        role === undefined
          ? createReferenceObject({
              kind: "resource_role",
              body: { ...written(values), org_node_id: values.org_node_id ?? "" },
            })
          : updateReferenceObject(role.resource_role_id, {
              kind: "resource_role",
              body: { ...written(values), lock_version: role.lock_version },
            })
      }
    />
  );
}

/**
 * The dialog of the list of the calendars, while its form is open: a label already held by another
 * calendar, deactivated ones counted (409 `ALREADY_EXISTS`, WF-REF-0110), names it by its identifier
 * when the page shows it, generically otherwise.
 */
export function CalendarDialog({
  names,
}: {
  /** The names of the calendars of the page, by identifier. */
  readonly names: ObjectNames;
}) {
  const t = useTranslations("reference");
  const columns = useTranslations("grid.columns");
  const days = useTranslations("admin.schedule.weekdays");
  const locale = useLocale();
  const form = useListForm();
  if (form === undefined) {
    return null;
  }
  const { row, ...rest } = form;
  const calendar = row as Calendar | undefined;
  const hours = (values: Draft) =>
    Object.fromEntries(DAYS.map((day) => [day, values[`weekly_hours/${day}`] ?? ""])) as Record<
      (typeof DAYS)[number],
      string
    >;
  const body = (values: Draft) => ({ label: values.label ?? "", weekly_hours: hours(values) });
  return (
    <ReferenceForm
      {...rest}
      title={
        calendar === undefined
          ? t("calendarForm.create")
          : t("modifyNamed", { name: calendar.label })
      }
      hint={t("calendarForm.hint")}
      creating={calendar === undefined}
      names={names}
      fields={[
        required("label", columns("label"), LABEL_LENGTH),
        ...DAYS.map((day): FormField => ({
          name: `weekly_hours/${day}`,
          label: days(day),
          control: "number",
          required: true,
        })),
      ]}
      initial={
        calendar === undefined
          ? {}
          : {
              label: calendar.label,
              ...Object.fromEntries(
                DAYS.map((day) => [
                  `weekly_hours/${day}`,
                  editableDecimal(calendar.weekly_hours[day], locale),
                ]),
              ),
            }
      }
      ask={(values) =>
        calendar === undefined
          ? createReferenceObject({ kind: "calendar", body: body(values) })
          : updateReferenceObject(calendar.calendar_id, {
              kind: "calendar",
              body: { ...body(values), lock_version: calendar.lock_version },
            })
      }
    />
  );
}
