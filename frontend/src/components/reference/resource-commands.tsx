// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The forms and the commands of the settings of the resources (FBS-3.2, EP-02/L43b), in dialogs over
 * their lists (`ReferenceForm`), offered to a session that may modify them:
 *
 * - a node of the organisation by its code, unique, its name and its parent — none for a root —
 *   (WF-REF-0070): an active node takes place under an active one alone, no active object remaining
 *   in a closed service, a deactivated one moves where one wants (WF-REF-0080, `updateOrgNode`);
 *   never under itself nor under one of its descendants, which it takes along;
 * - a resource role by its name, its node, its category of labour and its calendar — the three
 *   attachments required, among the active objects (WF-REF-0090) — and its single capacity, the hours
 *   a month and the headcount they stand for (WF-REF-0100); its node is set at its creation, a role
 *   being recreated under another rather than moved (§3.4.4.2.1): its modification names it, and
 *   leaves it;
 * - a calendar by its name and its seven values of hours, from Monday, and nothing else
 *   (WF-REF-0110).
 *
 * The designation of the default calendar is that of `calendar-default.tsx`.
 */
"use client";

import { useLocale, useTranslations } from "next-intl";

import { createReferenceObject, updateReferenceObject } from "@/api/actions/reference";
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

/**
 * The parents a node may take, from those of the tree read: the parent it has is offered all the
 * same — WF-REF-0080 leaves a deactivated node under a deactivated parent —, in its place when the
 * tree read holds it, marked when it is not active. One the tree read does not hold — read without
 * the deactivated ones — is not active, and is marked: placed under its own parent, at its depth,
 * when the rows of the list name it and the tree holds that one; at the end and set in by nothing
 * otherwise, never seeming to be under a node it is not under.
 */
function parentsOf(
  node: OrgNode | undefined,
  nodes: readonly Choice[],
  rows: readonly OrgNode[],
): Offered[] {
  const every = node?.is_active === false;
  const tree = outside(nodes, node?.org_node_id);
  if (node?.parent_id === null || node?.parent_id === undefined) {
    return offered(tree, undefined, every);
  }
  const attached = { id: node.parent_id, label: node.parent_label ?? "" };
  return nodes.some((each) => each.id === attached.id)
    ? offered(tree, attached, every)
    : placed(
        offered(tree, undefined, every),
        attached,
        rows.find((row) => row.org_node_id === attached.id),
      );
}

/**
 * A parent the tree read does not hold among the parents offered, marked: under its own parent, at
 * its depth, when its row is shown and the tree holds that one; at the end, set in by nothing,
 * otherwise.
 */
function placed(
  offers: readonly Offered[],
  { id, label }: { readonly id: string; readonly label: string },
  shown: OrgNode | undefined,
): Offered[] {
  const above = shown?.parent_id ?? null;
  const at = above === null ? -1 : offers.findIndex((offer) => offer.id === above);
  const parent: Offered = {
    id,
    code: shown?.code,
    label: shown?.label ?? label,
    level: at < 0 ? undefined : shown?.level,
    active: false,
    deactivated: true,
  };
  return at < 0
    ? [...offers, parent]
    : [...offers.slice(0, at + 1), parent, ...offers.slice(at + 1)];
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
  // An active node, or one created active, takes place under an active one alone (WF-REF-0080), a
  // deactivated one under any node read, its parent offered all the same.
  const parents = parentsOf(node, nodes, rows);
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

/** The dialog of the list of the calendars, while its form is open. */
export function CalendarDialog() {
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
