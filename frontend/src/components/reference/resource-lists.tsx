// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the resources (FBS-3.2, US-0250), each list a dense grid under its title (#301,
 * #511), in the order the server gave it, each column filtered by the server — the figures between
 * bounds (#533, #545, WF-IHM-0130): the nodes of the organisation, as a tree that folds, read whole — each by its
 * label set in by its depth under the node it is attached to, its code and its depth, in the order of
 * the tree the server gives (WF-REF-0070) —, filtered by code, depth and state, the ancestors of the
 * nodes retained shown; the resource roles, with their node, their category and their calendar, and
 * their single capacity (WF-REF-0090, WF-REF-0100), filtered by node, category, calendar and state,
 * and bounded on its monthly hours and its headcount, a page of the list the server pages; the
 * calendars, seven values of hours, the default one marked (WF-REF-0110, WF-REF-0120), filtered by
 * state and bounded on the hours of each day, a page too; the constants the units of duration
 * convert by (WF-PLA-0160). An object attached is named as the server resolves it. Every figure as
 * the API gives it. A deactivated object, which a list shows when the address asks for them, offers
 * its reactivation as the server lists it (WF-REF-0150, WF-IHM-0090); the forms that create and
 * modify belong to the epic of the reference data.
 *
 * A list says it is empty only when it holds nothing and nothing narrows it: a search or a filter
 * that retains nothing keeps its grid, the search shown to be changed; a page asked beyond its end
 * is no empty list, its pages say where it stands. A list whose bounds the API refused (422) is not
 * read: its filters stay, the bound refused said at its field, and a sentence stands for its grid.
 */
import { CalendarDays, Network, Timer, Users } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { ChoiceFilter } from "@/components/grid/choice-filter";
import {
  type Bounds,
  bounded,
  boundNames,
  type RefusedBounds,
  refusedSides,
} from "@/components/grid/filters";
import { ListPages } from "@/components/grid/list-pages";
import type { GridQuery } from "@/components/grid/query";
import { RangeFilter } from "@/components/grid/range-filter";
import type { GridPreferences } from "@/components/grid/settings";
import { formatDecimal } from "@/i18n/format";
import type { ListPage } from "@/navigation/pages";

import { listReads } from "./address";
import { Reactivations } from "./reactivation";
import { type NodeChoice, OrgNodeFilter, StateFilter, TextFilter } from "./reference-filters";
import { ResourceGrid } from "./resource-grid";
import {
  CALENDAR_ADDRESS,
  CALENDAR_STATE,
  type Calendar,
  type CalendarSort,
  calendarDay,
  DAYS,
  type Day,
  ORG_CODE,
  ORG_CODE_LENGTH,
  ORG_LEVEL,
  ORG_NODE_ADDRESS,
  ORG_STATE,
  type OrgNode,
  RESOURCE_ROLE_ADDRESS,
  ROLE_CALENDAR,
  ROLE_COST_CATEGORY,
  ROLE_HEADCOUNT,
  ROLE_MONTHLY_HOURS,
  ROLE_ORG_NODE,
  ROLE_STATE,
  type ResourceRole,
  type ResourceRoleSort,
} from "./resource-grids";
import { BoundsRefused, ReferenceSection } from "./section";

type DurationUnits = components["schemas"]["DurationUnits"];

/** What a list of the settings of the resources shows. */
interface ListProps<Row, Sort extends string> {
  readonly rows: readonly Row[];
  readonly query: GridQuery<Sort>;
  readonly preferences: GridPreferences | undefined;
  /**
   * Whether the session may read the deactivated objects of the settings of the resources, which
   * the filter of the state then offers.
   */
  readonly readsInactive: boolean;
}

/** A filter of the address, or none. */
function some(...values: readonly unknown[]): boolean {
  return values.some((value) => value !== undefined);
}

/** The parameters of the address that bound some columns, both sides of each. */
function boundReads(...columns: readonly string[]): string[] {
  return columns.flatMap((column) => Object.values(boundNames(column)));
}

/** The parameters of the address the tree reads, its filters among them. */
const ORG_READS = listReads(
  ORG_NODE_ADDRESS,
  ORG_CODE,
  ORG_LEVEL,
  ORG_STATE,
  ...boundReads(ORG_LEVEL),
);

/** What the tree of the organisation is filtered on, as the address asks it. */
export interface OrgNodeFilters {
  readonly code: string | undefined;
  readonly level: number | undefined;
  readonly state: boolean | undefined;
  /** The bounds of the depth, besides the one depth chosen (`level`). */
  readonly levels: Bounds;
}

/**
 * The nodes of the organisation, as a tree that folds, in the order the server gives it, filtered
 * on its code, its depth — among those of the whole tree (`levels`) — and its state.
 */
export function OrgNodeList({
  rows,
  query,
  preferences,
  readsInactive,
  filters,
  levels,
  refused,
}: ListProps<OrgNode, never> & {
  readonly filters: OrgNodeFilters;
  /** The depths of the whole tree, from the first, which the filter of the depth offers. */
  readonly levels: readonly number[];
  /** The bounds of the depth the API refused, the tree narrowed unread; none when it was read. */
  readonly refused?: RefusedBounds | undefined;
}) {
  const t = useTranslations("reference");
  const columns = useTranslations("grid.columns");
  const narrowed =
    some(query.search, filters.code, filters.level, filters.state) || bounded(filters.levels);
  return (
    <ReferenceSection
      title={t("orgNodes.title")}
      icon={Network}
      empty={
        rows.length === 0 && !narrowed && refused === undefined ? t("orgNodes.none") : undefined
      }
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <TextFilter
          name={ORG_CODE}
          label={t("orgNodes.codeFilter")}
          value={filters.code}
          length={ORG_CODE_LENGTH}
        />
        <ChoiceFilter
          name={ORG_LEVEL}
          label={t("orgNodes.levelFilter")}
          every={t("orgNodes.everyLevel")}
          choices={levels.map((level) => ({ value: level.toString(), text: level.toString() }))}
          chosen={filters.level?.toString()}
        />
        {readsInactive ? (
          <StateFilter
            name={ORG_STATE}
            label={t("stateFilter.of", { list: t("orgNodes.title") })}
            chosen={filters.state}
          />
        ) : null}
      </div>
      <RangeFilter
        label={t("boundsOf", { list: t("orgNodes.title") })}
        kind="level"
        columns={[
          {
            column: ORG_LEVEL,
            label: columns("level"),
            bounds: filters.levels,
            refused: refusedSides(refused, "level"),
          },
        ]}
      />
      {refused === undefined ? (
        <Reactivations reads={ORG_READS}>
          <ResourceGrid
            kind="orgNodes"
            rows={rows}
            query={query}
            preferences={preferences}
            narrowing={{
              search: query.search,
              code: filters.code,
              level: filters.level,
              state: filters.state,
              least: filters.levels.min,
              most: filters.levels.max,
            }}
          />
        </Reactivations>
      ) : (
        <BoundsRefused />
      )}
    </ReferenceSection>
  );
}

/** A category of cost or a calendar the roles may be filtered on. */
export interface Attached {
  readonly id: string;
  readonly label: string;
  /** Its code, for a category. */
  readonly code?: string;
}

/** What the roles are filtered on, as the address asks it. */
export interface RoleFilters {
  readonly orgNode: string | undefined;
  readonly category: string | undefined;
  readonly calendar: string | undefined;
  readonly state: boolean | undefined;
  readonly monthlyHours: Bounds;
  readonly headcount: Bounds;
}

/** The parameters of the address the roles read, their filters among them. */
const ROLE_READS = listReads(
  RESOURCE_ROLE_ADDRESS,
  ROLE_ORG_NODE,
  ROLE_COST_CATEGORY,
  ROLE_CALENDAR,
  ROLE_STATE,
  ...boundReads(ROLE_MONTHLY_HOURS, ROLE_HEADCOUNT),
);

/**
 * The resource roles of a page of the list, each with its node, its category and its calendar —
 * named as the server resolves them, active or not (WF-REF-0150) —, its capacity in hours a month
 * and the headcount they stand for, and its state; filtered by the node, the category, the calendar
 * and the state the address names, and bounded on the monthly hours and the headcount. A list of
 * choices the API refuses (`undefined`) offers no filter.
 */
export function ResourceRoleList({
  rows,
  page,
  query,
  preferences,
  readsInactive,
  nodes,
  categories,
  calendars,
  filters,
  refused,
}: ListProps<ResourceRole, ResourceRoleSort> & {
  readonly page: ListPage;
  /** The nodes of organisation the roles may be restricted to, in the order of the tree. */
  readonly nodes: readonly NodeChoice[];
  /** The categories of cost the roles may be restricted to, in the order of the server. */
  readonly categories: readonly Attached[] | undefined;
  /** The calendars the roles may be restricted to, in the order of the server. */
  readonly calendars: readonly Attached[];
  readonly filters: RoleFilters;
  /** The bounds the API refused, the list then unread; none when it was read. */
  readonly refused?: RefusedBounds | undefined;
}) {
  const t = useTranslations("reference");
  const columns = useTranslations("grid.columns");
  const title = t("resourceRoles.title");
  const offset = RESOURCE_ROLE_ADDRESS.offset;
  const narrowed =
    some(query.search, filters.orgNode, filters.category, filters.calendar, filters.state) ||
    bounded(filters.monthlyHours) ||
    bounded(filters.headcount);
  return (
    <ReferenceSection
      title={title}
      icon={Users}
      empty={
        page.total === 0 && !narrowed && refused === undefined ? t("resourceRoles.none") : undefined
      }
    >
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <OrgNodeFilter name={ROLE_ORG_NODE} nodes={nodes} chosen={filters.orgNode} page={offset} />
        {categories === undefined ? null : (
          <ChoiceFilter
            name={ROLE_COST_CATEGORY}
            label={t("resourceRoles.costCategoryFilter")}
            every={t("resourceRoles.everyCostCategory")}
            choices={categories.map((category) => ({
              value: category.id,
              text: t("codedChoice", { code: category.code ?? "", label: category.label }),
            }))}
            chosen={filters.category}
            page={offset}
          />
        )}
        <ChoiceFilter
          name={ROLE_CALENDAR}
          label={t("resourceRoles.calendarFilter")}
          every={t("resourceRoles.everyCalendar")}
          choices={calendars.map((calendar) => ({ value: calendar.id, text: calendar.label }))}
          chosen={filters.calendar}
          page={offset}
        />
        {readsInactive ? (
          <StateFilter
            name={ROLE_STATE}
            label={t("stateFilter.of", { list: title })}
            chosen={filters.state}
            page={offset}
          />
        ) : null}
      </div>
      <RangeFilter
        label={t("boundsOf", { list: title })}
        kind="decimal"
        columns={[
          {
            column: ROLE_MONTHLY_HOURS,
            label: columns("monthlyHours"),
            bounds: filters.monthlyHours,
            refused: refusedSides(refused, "monthly_hours"),
          },
          {
            column: ROLE_HEADCOUNT,
            label: columns("headcount"),
            bounds: filters.headcount,
            refused: refusedSides(refused, "headcount"),
          },
        ]}
        page={offset}
      />
      {refused === undefined ? (
        <>
          <Reactivations reads={ROLE_READS}>
            <ResourceGrid
              kind="resourceRoles"
              rows={rows}
              page={page}
              query={query}
              preferences={preferences}
            />
          </Reactivations>
          <ListPages
            list={{ page: offset, reads: ROLE_READS }}
            title={title}
            page={page}
            shown={rows.length}
          />
        </>
      ) : (
        <BoundsRefused />
      )}
    </ReferenceSection>
  );
}

/** The parameters of the address the calendars read, their filters among them. */
const CALENDAR_READS = listReads(
  CALENDAR_ADDRESS,
  CALENDAR_STATE,
  ...boundReads(...DAYS.map(calendarDay)),
);

/** The bounds of the hours of each day of the calendars, as the address asks them. */
export type DayBounds = Readonly<Record<Day, Bounds>>;

/**
 * The calendars of a page of the list, each by its seven values of hours from Monday, the default
 * one marked, filtered by state and bounded on the hours of each day.
 */
export function CalendarList({
  rows,
  page,
  query,
  preferences,
  readsInactive,
  state,
  hours,
  refused,
}: ListProps<Calendar, CalendarSort> & {
  readonly page: ListPage;
  /** The state the address filters the calendars on; none, every state. */
  readonly state: boolean | undefined;
  /** The bounds of the hours of each day the address asks. */
  readonly hours: DayBounds;
  /** The bounds the API refused, the list then unread; none when it was read. */
  readonly refused?: RefusedBounds | undefined;
}) {
  const t = useTranslations("reference");
  const columns = useTranslations("grid.columns");
  const title = t("calendars.title");
  const narrowed = some(query.search, state) || DAYS.some((day) => bounded(hours[day]));
  return (
    <ReferenceSection
      title={title}
      icon={CalendarDays}
      empty={
        page.total === 0 && !narrowed && refused === undefined ? t("calendars.none") : undefined
      }
    >
      {readsInactive ? (
        <StateFilter
          name={CALENDAR_STATE}
          label={t("stateFilter.of", { list: title })}
          chosen={state}
          page={CALENDAR_ADDRESS.offset}
        />
      ) : null}
      <RangeFilter
        label={t("boundsOf", { list: title })}
        kind="decimal"
        columns={DAYS.map((day) => ({
          column: calendarDay(day),
          label: columns(day),
          bounds: hours[day],
          refused: refusedSides(refused, day),
        }))}
        page={CALENDAR_ADDRESS.offset}
      />
      {refused === undefined ? (
        <>
          <Reactivations reads={CALENDAR_READS}>
            <ResourceGrid
              kind="calendars"
              rows={rows}
              page={page}
              query={query}
              preferences={preferences}
            />
          </Reactivations>
          <ListPages
            list={{ page: CALENDAR_ADDRESS.offset, reads: CALENDAR_READS }}
            title={title}
            page={page}
            shown={rows.length}
          />
        </>
      ) : (
        <BoundsRefused />
      )}
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
