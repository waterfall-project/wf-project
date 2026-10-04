// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the resources (FBS-3.2, US-0250), in dense tables, in the order the server gave
 * them: the nodes of the organisation, each with the node it is attached to (WF-REF-0070); the
 * resource roles, with their node, their category and their calendar, and their single capacity
 * (WF-REF-0090, WF-REF-0100); the calendars, seven values of hours, the default one marked
 * (WF-REF-0110, WF-REF-0120); the constants the units of duration convert by (WF-PLA-0160). An
 * object attached is named as the server resolves it. Every figure as the API gives it. Read
 * only: the forms belong to the epic of the reference data.
 */
import { CalendarDays, CalendarCheck, Network, Timer, Users } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { CELL, ICON, ListTable } from "@/components/projects/project-tables";
import { TableCell, TableRow } from "@/components/ui/table";
import { formatDecimal } from "@/i18n/format";

import { ActiveState, ReferenceSection } from "./section";

type OrgNode = components["schemas"]["OrgNode"];
type ResourceRole = components["schemas"]["ResourceRole"];
type Calendar = components["schemas"]["Calendar"];
type DurationUnits = components["schemas"]["DurationUnits"];

/** The seven days of a calendar, from Monday, as the contract names them. */
const DAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const satisfies readonly (keyof Calendar["weekly_hours"])[];

/** The nodes of the organisation, each with the node it is attached to, the root with none. */
export function OrgNodeList({ nodes }: { readonly nodes: readonly OrgNode[] }) {
  const t = useTranslations("reference.orgNodes");
  const columns = useTranslations("reference.columns");
  return (
    <ReferenceSection
      title={t("title")}
      icon={Network}
      empty={nodes.length === 0 ? t("none") : undefined}
    >
      <ListTable label={t("title")} columns={[columns("label"), t("parent"), columns("state")]}>
        {nodes.map((node) => (
          <TableRow key={node.org_node_id}>
            <TableCell className={CELL}>{node.label}</TableCell>
            <TableCell className={CELL}>{node.parent_label ?? t("root")}</TableCell>
            <TableCell className={CELL}>
              <ActiveState active={node.is_active} />
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </ReferenceSection>
  );
}

/**
 * The resource roles, each with its node, its category and its calendar — named as the server
 * resolves them, active or not (WF-REF-0150) —, its capacity in hours a month and the headcount
 * they stand for, and its state.
 */
export function ResourceRoleList({ roles }: { readonly roles: readonly ResourceRole[] }) {
  const t = useTranslations("reference.resourceRoles");
  const columns = useTranslations("reference.columns");
  const locale = useLocale();
  return (
    <ReferenceSection
      title={t("title")}
      icon={Users}
      empty={roles.length === 0 ? t("none") : undefined}
    >
      <ListTable
        label={t("title")}
        columns={[
          columns("label"),
          t("orgNode"),
          t("costCategory"),
          t("calendar"),
          t("monthlyHours"),
          t("headcount"),
          columns("state"),
        ]}
      >
        {roles.map((role) => (
          <TableRow key={role.resource_role_id}>
            <TableCell className={CELL}>{role.label}</TableCell>
            <TableCell className={CELL}>{role.org_node_label}</TableCell>
            <TableCell className={CELL}>{role.cost_category_label}</TableCell>
            <TableCell className={CELL}>{role.calendar_label}</TableCell>
            <TableCell className={`${CELL} text-right tabular-nums`}>
              {formatDecimal(role.capacity.monthly_hours, locale)}
            </TableCell>
            <TableCell className={`${CELL} text-right tabular-nums`}>
              {formatDecimal(role.capacity.headcount, locale)}
            </TableCell>
            <TableCell className={CELL}>
              <ActiveState active={role.is_active} />
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </ReferenceSection>
  );
}

/** The calendars, each by its seven values of hours from Monday, the default one marked. */
export function CalendarList({ calendars }: { readonly calendars: readonly Calendar[] }) {
  const t = useTranslations("reference.calendars");
  const columns = useTranslations("reference.columns");
  const locale = useLocale();
  return (
    <ReferenceSection
      title={t("title")}
      icon={CalendarDays}
      empty={calendars.length === 0 ? t("none") : undefined}
    >
      <ListTable
        label={t("title")}
        columns={[
          columns("label"),
          ...DAYS.map((day) => t(`days.${day}`)),
          t("default"),
          columns("state"),
        ]}
      >
        {calendars.map((calendar) => (
          <TableRow key={calendar.calendar_id}>
            <TableCell className={CELL}>{calendar.label}</TableCell>
            {DAYS.map((day) => (
              <TableCell key={day} className={`${CELL} text-right tabular-nums`}>
                {formatDecimal(calendar.weekly_hours[day], locale)}
              </TableCell>
            ))}
            <TableCell className={CELL}>
              {calendar.is_default ? (
                <span className="inline-flex items-center gap-1.5">
                  <CalendarCheck aria-hidden="true" className={ICON} />
                  {t("isDefault")}
                </span>
              ) : null}
            </TableCell>
            <TableCell className={CELL}>
              <ActiveState active={calendar.is_active} />
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </ReferenceSection>
  );
}

/** The three constants the days, the weeks and the months of work convert into hours by. */
export function DurationUnitFacts({ units }: { readonly units: DurationUnits }) {
  const t = useTranslations("reference.durationUnits");
  const locale = useLocale();
  const facts = [
    ["hoursPerDay", units.hours_per_day],
    ["hoursPerWeek", units.hours_per_week],
    ["daysPerMonth", units.days_per_month],
  ] as const;
  return (
    <ReferenceSection title={t("title")} icon={Timer}>
      <dl className="grid w-fit grid-cols-[auto_auto] gap-x-6 gap-y-1 text-sm">
        {facts.map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="text-muted-foreground">{t(key)}</dt>
            <dd className="text-right tabular-nums">{formatDecimal(value, locale)}</dd>
          </div>
        ))}
      </dl>
    </ReferenceSection>
  );
}
