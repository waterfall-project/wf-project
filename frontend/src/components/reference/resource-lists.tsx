// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the resources (FBS-3.2, US-0250), each list a dense grid under its title (#301,
 * #511), in the order the server gave it: the nodes of the organisation, as a tree that folds —
 * each by its label set in by its depth under the node it is attached to, its code and its depth,
 * in the order of the tree the server gives (WF-REF-0070); the resource roles, with their node,
 * their category and their calendar, and their single capacity (WF-REF-0090, WF-REF-0100),
 * filtered by node; the calendars, seven values of hours, the default one marked (WF-REF-0110,
 * WF-REF-0120); the constants the units of duration convert by (WF-PLA-0160). An object attached
 * is named as the server resolves it. Every figure as the API gives it. A deactivated object,
 * which a list shows when the address asks for them, offers its reactivation (WF-REF-0150); the
 * forms that create and modify belong to the epic of the reference data.
 *
 * A list says it is empty only when nothing narrows it: a search or a filter that retains nothing
 * keeps its grid, the search shown to be changed.
 */
import { Network, Timer, Users, CalendarDays } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import type { GridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import { formatDecimal } from "@/i18n/format";

import { listReads } from "./address";
import { Reactivations } from "./reactivation";
import { type NodeChoice, OrgNodeFilter } from "./reference-filters";
import { ResourceGrid } from "./resource-grid";
import {
  CALENDAR_ADDRESS,
  type Calendar,
  type CalendarSort,
  ORG_NODE_ADDRESS,
  type OrgNode,
  RESOURCE_ROLE_ADDRESS,
  ROLE_ORG_NODE,
  type ResourceRole,
  type ResourceRoleSort,
} from "./resource-grids";
import { ReferenceSection } from "./section";

type DurationUnits = components["schemas"]["DurationUnits"];

/** What a list of the settings of the resources shows. */
interface ListProps<Row, Sort extends string> {
  readonly rows: readonly Row[];
  readonly query: GridQuery<Sort>;
  readonly preferences: GridPreferences | undefined;
  /** Whether the session may modify the settings of the resources (`platformOffer`). */
  readonly reactivable: boolean;
}

/** What a list says when its answer holds nothing: that it is empty, unless something narrows it. */
function emptiness(rows: readonly unknown[], narrowed: boolean, none: string): string | undefined {
  return rows.length === 0 && !narrowed ? none : undefined;
}

/** The nodes of the organisation, as a tree that folds, in the order the server gives it. */
export function OrgNodeList({ rows, query, preferences, reactivable }: ListProps<OrgNode, never>) {
  const t = useTranslations("reference.orgNodes");
  return (
    <ReferenceSection
      title={t("title")}
      icon={Network}
      empty={emptiness(rows, query.search !== undefined, t("none"))}
    >
      <Reactivations reads={listReads(ORG_NODE_ADDRESS)}>
        <ResourceGrid
          kind="orgNodes"
          rows={rows}
          query={query}
          preferences={preferences}
          reactivable={reactivable}
        />
      </Reactivations>
    </ReferenceSection>
  );
}

/**
 * The resource roles, each with its node, its category and its calendar — named as the server
 * resolves them, active or not (WF-REF-0150) —, its capacity in hours a month and the headcount
 * they stand for, and its state; filtered by the node the address names, among those of the tree.
 */
export function ResourceRoleList({
  rows,
  query,
  preferences,
  reactivable,
  nodes,
  orgNode,
}: ListProps<ResourceRole, ResourceRoleSort> & {
  /** The nodes of organisation the roles may be restricted to, in the order of the tree. */
  readonly nodes: readonly NodeChoice[];
  /** The node the address restricts the roles to, if any. */
  readonly orgNode: string | undefined;
}) {
  const t = useTranslations("reference.resourceRoles");
  return (
    <ReferenceSection
      title={t("title")}
      icon={Users}
      empty={emptiness(rows, query.search !== undefined || orgNode !== undefined, t("none"))}
    >
      <OrgNodeFilter name={ROLE_ORG_NODE} nodes={nodes} chosen={orgNode} />
      <Reactivations reads={listReads(RESOURCE_ROLE_ADDRESS, ROLE_ORG_NODE)}>
        <ResourceGrid
          kind="resourceRoles"
          rows={rows}
          query={query}
          preferences={preferences}
          reactivable={reactivable}
        />
      </Reactivations>
    </ReferenceSection>
  );
}

/** The calendars, each by its seven values of hours from Monday, the default one marked. */
export function CalendarList({
  rows,
  query,
  preferences,
  reactivable,
}: ListProps<Calendar, CalendarSort>) {
  const t = useTranslations("reference.calendars");
  return (
    <ReferenceSection
      title={t("title")}
      icon={CalendarDays}
      empty={emptiness(rows, query.search !== undefined, t("none"))}
    >
      <Reactivations reads={listReads(CALENDAR_ADDRESS)}>
        <ResourceGrid
          kind="calendars"
          rows={rows}
          query={query}
          preferences={preferences}
          reactivable={reactivable}
        />
      </Reactivations>
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
