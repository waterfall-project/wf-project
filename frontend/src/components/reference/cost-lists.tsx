// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The natures and the categories of cost (FBS-3.1.1, US-0250), each a dense grid under its title
 * (#510), a page of the list the server pages, in the order it gave it, each column sorted and
 * filtered by the server (WF-IHM-0060, WF-IHM-0130): each nature by its code, its name and its type
 * (WF-REF-0030), filtered by type and by state; each category by its code, its name, its nature and
 * its accounting code (WF-REF-0040), filtered by nature — chosen among every nature the session
 * reads — and by state. A deactivated one, which the lists show when the address asks for them,
 * offers its reactivation as the server lists it (WF-REF-0150, WF-IHM-0090). A session that may
 * modify the cost settings creates a nature or a category from the head of its list, modifies each
 * from its row, and deactivates one an active object lists the deactivation of (EP-02/L43a,
 * `cost-commands.tsx`); no command deletes one (WF-REF-0010).
 *
 * A list says it is empty only when it holds nothing and nothing narrows it: a search or a filter
 * that retains nothing keeps its grid, the search shown to be changed; a page asked beyond its end
 * is no empty list, its pages say where it stands.
 *
 * Beside the grid of the hourly rates, its filters (`RateFilterBar`): the state of the categories,
 * and the bounds of the rate of a year chosen among those of the grid (#545); bounds the API
 * refused (422) are said at their field, the grid unread.
 */
import { Layers, Tags } from "lucide-react";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import { ChoiceFilter } from "@/components/grid/choice-filter";
import { type Bounds, type RefusedBounds, refusedSides } from "@/components/grid/filters";
import { ListPages } from "@/components/grid/list-pages";
import { CONTRACT_ADDRESS, type GridQuery } from "@/components/grid/query";
import { RangeFilter } from "@/components/grid/range-filter";
import type { GridPreferences } from "@/components/grid/settings";
import { ValuesFilter } from "@/components/grid/values-filter";
import type { ListPage } from "@/navigation/pages";

import { listReads } from "./address";
import { CostCommands, CostDialog, CreateCostCommand } from "./cost-commands";
import { CostGrid } from "./cost-grid";
import {
  CATEGORY_COST_TYPE,
  CATEGORY_STATE,
  COST_CATEGORY_ADDRESS,
  COST_TYPE_ADDRESS,
  COST_TYPE_KIND_VALUES,
  COST_TYPE_KINDS,
  COST_TYPE_STATE,
  type CostCategory,
  type CostCategorySort,
  type CostType,
  type CostTypeKind,
  type CostTypeSort,
} from "./cost-grids";
import type { NatureChoice } from "./cost-kinds";
import { RATE_COLUMN, RATE_STATE, RATE_YEAR } from "./rate-columns";
import { Reactivations } from "./reactivation";
import { StateFilter } from "./reference-filters";
import { ReferenceSection } from "./section";

/** What a list of the natures or the categories shows. */
interface ListProps<Row, Sort extends string> {
  readonly rows: readonly Row[];
  readonly page: ListPage;
  readonly query: GridQuery<Sort>;
  readonly preferences: GridPreferences | undefined;
  /** The state the address filters the list on; none, every state. */
  readonly state: boolean | undefined;
  /**
   * Whether the session may read the deactivated objects of the cost settings, which the filter of
   * the state then offers.
   */
  readonly readsInactive: boolean;
  /** Whether the session may modify the cost settings (`platformOffer`): it creates and modifies. */
  readonly editable: boolean;
}

/**
 * The body of a list: its filters, its grid and its pages — or, empty with nothing narrowing it, what
 * says so —, the grid within the region that tells the refusals of its commands, where its form opens
 * too, on an empty list as well.
 */
function ListBody({
  empty,
  reads,
  filters,
  grid,
  pages,
}: {
  /** What the list says when it is empty and nothing narrows it; `undefined` when it is not. */
  readonly empty: string | undefined;
  readonly reads: readonly string[];
  readonly filters: ReactNode;
  readonly grid: ReactNode;
  readonly pages: ReactNode;
}) {
  return (
    <>
      {empty === undefined ? filters : null}
      <Reactivations reads={reads}>
        {empty === undefined ? grid : <p className="text-sm text-muted-foreground">{empty}</p>}
        <CostDialog />
      </Reactivations>
      {empty === undefined ? pages : null}
    </>
  );
}

/** The parameters of the address the natures read, their filters among them. */
const COST_TYPE_READS = listReads(COST_TYPE_ADDRESS, COST_TYPE_KINDS, COST_TYPE_STATE);

/** The parameters of the address the categories read, their filters among them. */
const COST_CATEGORY_READS = listReads(COST_CATEGORY_ADDRESS, CATEGORY_COST_TYPE, CATEGORY_STATE);

/** The natures of cost of a page, each by its code, its name, its type and its state. */
export function CostTypeList({
  rows,
  page,
  query,
  preferences,
  state,
  readsInactive,
  editable,
  kinds,
}: ListProps<CostType, CostTypeSort> & {
  /** The types the address restricts the natures to; none, every one. */
  readonly kinds: readonly CostTypeKind[];
}) {
  const t = useTranslations("reference");
  const named = useTranslations("enums.CostTypeKind");
  const title = t("costTypes.title");
  const offset = COST_TYPE_ADDRESS.offset;
  const narrowed = query.search !== undefined || kinds.length > 0 || state !== undefined;
  return (
    <CostCommands kind="cost_type" natures={[]}>
      <ReferenceSection
        title={title}
        icon={Layers}
        commands={editable ? <CreateCostCommand kind="cost_type" /> : undefined}
      >
        <ListBody
          empty={page.total === 0 && !narrowed ? t("costTypes.none") : undefined}
          reads={COST_TYPE_READS}
          filters={
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <ValuesFilter
                name={COST_TYPE_KINDS}
                label={t("costTypes.kindFilter")}
                every={t("costTypes.everyKind")}
                values={COST_TYPE_KIND_VALUES.map((kind) => ({ value: kind, text: named(kind) }))}
                chosen={kinds}
                page={offset}
              />
              {readsInactive ? (
                <StateFilter
                  name={COST_TYPE_STATE}
                  label={t("stateFilter.of", { list: title })}
                  chosen={state}
                  page={offset}
                />
              ) : null}
            </div>
          }
          grid={
            <CostGrid
              kind="costTypes"
              rows={rows}
              page={page}
              query={query}
              preferences={preferences}
              editable={editable}
            />
          }
          pages={
            <ListPages
              list={{ page: offset, reads: COST_TYPE_READS }}
              title={title}
              page={page}
              shown={rows.length}
            />
          }
        />
      </ReferenceSection>
    </CostCommands>
  );
}

/**
 * The categories of cost of a page, each by its code, its name, the nature it is attached to —
 * named as the server resolves it, active or not (WF-REF-0150) —, its accounting code, documentary,
 * and its state; filtered by the nature and the state the address names.
 */
export function CostCategoryList({
  rows,
  page,
  query,
  preferences,
  state,
  readsInactive,
  editable,
  natures,
  nature,
}: ListProps<CostCategory, CostCategorySort> & {
  /** The natures the categories may be restricted to or attached to, in the order of the server. */
  readonly natures: readonly NatureChoice[];
  /** The nature the address restricts the categories to, if any. */
  readonly nature: string | undefined;
}) {
  const t = useTranslations("reference");
  const title = t("costCategories.title");
  const offset = COST_CATEGORY_ADDRESS.offset;
  const narrowed = query.search !== undefined || nature !== undefined || state !== undefined;
  return (
    <CostCommands kind="cost_category" natures={natures}>
      <ReferenceSection
        title={title}
        icon={Tags}
        commands={editable ? <CreateCostCommand kind="cost_category" /> : undefined}
      >
        <ListBody
          empty={page.total === 0 && !narrowed ? t("costCategories.none") : undefined}
          reads={COST_CATEGORY_READS}
          filters={
            <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
              <ChoiceFilter
                name={CATEGORY_COST_TYPE}
                label={t("costCategories.costTypeFilter")}
                every={t("costCategories.everyCostType")}
                choices={natures.map((choice) => ({
                  value: choice.id,
                  text: t("codedChoice", { code: choice.code, label: choice.label }),
                }))}
                chosen={nature}
                page={offset}
              />
              {readsInactive ? (
                <StateFilter
                  name={CATEGORY_STATE}
                  label={t("stateFilter.of", { list: title })}
                  chosen={state}
                  page={offset}
                />
              ) : null}
            </div>
          }
          grid={
            <CostGrid
              kind="costCategories"
              rows={rows}
              page={page}
              query={query}
              preferences={preferences}
              editable={editable}
            />
          }
          pages={
            <ListPages
              list={{ page: offset, reads: COST_CATEGORY_READS }}
              title={title}
              page={page}
              shown={rows.length}
            />
          }
        />
      </ReferenceSection>
    </CostCommands>
  );
}

/** What the grid of the hourly rates is filtered on, as the address asks it. */
export interface RateFilters {
  /** The state the address filters the categories on; none, every state. */
  readonly state: boolean | undefined;
  /** The year whose rate is bounded, as the address names it; none when it names none. */
  readonly year: number | undefined;
  readonly rate: Bounds;
}

/**
 * The filters of the grid of the hourly rates, under the names of the contract: the state of the
 * categories, for a session that may read the deactivated ones; the bounds of the rate of a year,
 * chosen among the years given — those of the grid —, the last one when the address names none. The
 * parameters the API refused (`refused`, 422) are said at their fields. Without a year to offer —
 * the grid unread, and the address naming none —, the rate is not bounded.
 */
export function RateFilterBar({
  filters,
  years,
  readsInactive,
  refused,
}: {
  readonly filters: RateFilters;
  /** The years the rate may be bounded for, in their order. */
  readonly years: readonly number[];
  readonly readsInactive: boolean;
  /** The parameters of the bounds the API refused, by their names; none when it refused none. */
  readonly refused: RefusedBounds | undefined;
}) {
  const t = useTranslations("reference");
  const names = useTranslations("grid.names");
  const list = names("hourlyRates");
  const offset = CONTRACT_ADDRESS.offset;
  return (
    <div className="flex flex-wrap items-start gap-x-6 gap-y-2">
      {readsInactive ? (
        <StateFilter
          name={RATE_STATE}
          label={t("stateFilter.of", { list })}
          chosen={filters.state}
          page={offset}
        />
      ) : null}
      {years.length === 0 ? null : (
        <RangeFilter
          label={t("boundsOf", { list })}
          kind="money"
          scope={{
            name: RATE_YEAR,
            label: t("rates.bounds.year"),
            choices: years.map((year) => ({ value: year.toString(), text: year.toString() })),
            chosen: (filters.year ?? years.at(-1))?.toString(),
            refused: refused?.get(RATE_YEAR),
          }}
          columns={[
            {
              column: RATE_COLUMN,
              label: t("rates.bounds.rate"),
              bounds: filters.rate,
              refused: refusedSides(refused, RATE_COLUMN),
            },
          ]}
          page={offset}
        />
      )}
    </div>
  );
}
