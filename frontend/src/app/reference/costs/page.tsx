// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the costs (FBS-3.1, US-0250), outside any project: the currency of the
 * installation, every amount expressed in it (WF-REF-0140), and beside it the name of the company
 * the exported files bear (WF-EXP-0020), modified where the session may modify the cost settings;
 * then, stacked one under the other in a page that scrolls, as the settings of the resources are
 * (US-0570, #1044), the natures and the categories of cost (FBS-3.1.1), two dense grids searched,
 * filtered, sorted and paged by the server, as the address asks under the names of each grid
 * (#510), and the grid of the hourly rates (FBS-3.1.2), a row for each category of labour and a
 * column for each year, on the dense grid, searched, filtered on the state of its categories and on
 * the bounds of the rate of a year, sorted and paged by the server under the names of the contract
 * (#509, #545), its cells entered where the session may modify the cost settings (WF-REF-0050).
 * Each grid keeps a height of its own, no taller than the window; its size is the rows per page the
 * account chose for it (WF-IHM-0060). Every figure as the API gives it: the front computes, sorts,
 * filters and pages nothing.
 *
 * The screen of reference of EP-25 (US-2080, #3071): each section in its card (`ReferenceCard`),
 * the creation of a nature or a category filled at the right of the title of its card, offered on
 * an empty list too; the card of the rates without a command beside its title, the column of a year
 * added from the end of the bar of its grid.
 *
 * Each list and the grid show the state their own filter says (WF-REF-0150, US-2090): the active
 * objects alone by default, said by the chip « Actifs (par défaut) », the deactivated ones alone, or
 * every one, the chip lifted — the address says it under the name of each grid, else the account
 * kept it with the settings of the grid (`stateOf`); the screen has no switch of its own, and
 * `include_inactive` in its address is no longer read (#3076). Only a session that bears the
 * permission of modifying the cost settings is offered the filter, without which the contract
 * refuses the deactivated objects (403): another reads the active ones alone. Each nature and each
 * category carries the command that reactivates it, as the server lists it. The categories are
 * filtered by a nature chosen among the active ones, read whole as a list of choices is (#303). A
 * session that may modify the cost settings creates and modifies the natures and the categories,
 * and deactivates them as each lists it (EP-02/L43a), the form of a category reading the type of
 * every nature, deactivated ones included (EP-02/L42g), and offering the active ones alone, whatever
 * the lists show; the service keeps what is
 * written, and the screen shows no mock-up notice. Bounds of the rate the API refuses (422) leave
 * the grid unread, the bound said at its field; any other read the API refuses, or cannot answer,
 * is thrown for the pages of the shell to say.
 */
import { Coins } from "lucide-react";
import type { Metadata } from "next";
import Link from "next/link";
import { useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import { readEveryPage } from "@/api/every-page";
import { type ExpectedRefusal, readOrFail, type ReadOrRefused, readOrRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { platformOffer } from "@/components/commands/offer";
import {
  bounded,
  readBounds,
  readValues,
  type RefusedBounds,
  refusedBounds,
} from "@/components/grid/filters";
import { PendingAddress } from "@/components/grid/pending-address";
import { asked, CONTRACT_ADDRESS, type GridQuery, readGridQuery } from "@/components/grid/query";
import {
  given,
  identifierOf,
  type KeptGrids,
  stateOf,
  stateQuery,
} from "@/components/reference/address";
import {
  CATEGORY_COST_TYPE,
  CATEGORY_STATE,
  COST_CATEGORY_ADDRESS,
  COST_CATEGORY_GRID_KEY,
  COST_CATEGORY_SORTS,
  COST_TYPE_ADDRESS,
  COST_TYPE_GRID_KEY,
  COST_TYPE_KIND_VALUES,
  COST_TYPE_KINDS,
  COST_TYPE_SORTS,
  COST_TYPE_STATE,
  type CostCategorySort,
  type CostTypeKind,
  type CostTypeSort,
} from "@/components/reference/cost-grids";
import { type CostType, type NatureChoice, natureChoice } from "@/components/reference/cost-kinds";
import {
  CostCategoryList,
  CostTypeList,
  RateFilterBar,
  type RateFilters,
} from "@/components/reference/cost-lists";
import {
  RATE_COLUMN,
  RATE_GRID_KEY,
  RATE_SORTS,
  RATE_STATE,
  RATE_YEAR,
  type RateSort,
  yearOf,
} from "@/components/reference/rate-columns";
import { type HourlyRateGrid, RateGrid } from "@/components/reference/rate-grid";
import { CompanyName, CompanySettings } from "@/components/reference/settings-forms";
import { BoundsRefused, ReferenceCard } from "@/components/reference/section";
import { FUNCTION_DENSITY, FUNCTION_ICONS, LEAF_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { buttonVariants } from "@/components/ui/button";
import { leafOf } from "@/navigation/functions";
import { type PageSearchParams, pageSearch, type SearchParameters } from "@/navigation/context";
import { offsetOf } from "@/navigation/pages";
import { type Permission, requestSession } from "@/session/request";

import { screenMetadata } from "../../title";
import { readReferenceSettings } from "../settings";

type ReferenceSettings = components["schemas"]["ReferenceSettings"];

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.costSettings");
}

/** The leaf of the correspondence of the actual costs, which the screen leads to (`make screens`). */
const MAPPING = leafOf("FBS-3.1.3");
const MappingIcon = LEAF_ICONS["FBS-3.1.3"];

/** The refusal of the bounds of the rate: an upper bound below the lower one (#545). */
const BOUNDS_REFUSED = [{ status: 422, code: "VALIDATION_FAILED" }] as const;

/**
 * The bounds of the rate of a year, under the names of the contract: asked only with their year,
 * without which the contract refuses them.
 */
function rateBounds({ year, rate }: RateFilters) {
  return year === undefined || !bounded(rate)
    ? {}
    : { rate_year: year, ...given("rate_min", rate.min), ...given("rate_max", rate.max) };
}

/** What the page asks of each list, as its address and the session say. */
interface CostQueries {
  /** Whether the session may modify the cost settings, and so reads the deactivated objects. */
  readonly editable: boolean;
  readonly rates: GridQuery<RateSort>;
  readonly rateOffset: number | undefined;
  readonly rateFilters: RateFilters;
  readonly types: GridQuery<CostTypeSort>;
  readonly typeOffset: number | undefined;
  readonly kinds: readonly CostTypeKind[];
  readonly typeState: boolean | undefined;
  readonly categories: GridQuery<CostCategorySort>;
  readonly categoryOffset: number | undefined;
  readonly nature: string | undefined;
  readonly categoryState: boolean | undefined;
}

/**
 * What the grid of the rates is filtered on: the state, and the bounds of the rate of a year — none
 * without a year the contract takes, which they go with.
 */
function readRateFilters(search: SearchParameters, state: boolean | undefined): RateFilters {
  const year = yearOf(search.get(RATE_YEAR));
  return {
    state,
    year,
    rate:
      year === undefined
        ? { min: undefined, max: undefined }
        : readBounds(search, RATE_COLUMN, "money"),
  };
}

/** What the page asks of each list, from its address, the sort each grid keeps and the session. */
function readQueries(
  search: SearchParameters,
  grids: KeptGrids | undefined,
  permissions: readonly Permission[],
): CostQueries {
  // The state each list shows: the address's, else the one its grid keeps, else the active alone.
  const state = (name: string, key: string) =>
    stateOf(search, name, grids?.[key]?.filters?.[name], permissions, "cost_settings.write");
  return {
    editable: platformOffer(permissions, "cost_settings") !== undefined,
    rates: readGridQuery(
      search,
      RATE_SORTS,
      grids?.[RATE_GRID_KEY]?.sort,
      CONTRACT_ADDRESS,
      grids?.[RATE_GRID_KEY]?.page_size,
    ),
    rateOffset: offsetOf(search.get(CONTRACT_ADDRESS.offset)),
    rateFilters: readRateFilters(search, state(RATE_STATE, RATE_GRID_KEY)),
    types: readGridQuery(
      search,
      COST_TYPE_SORTS,
      grids?.[COST_TYPE_GRID_KEY]?.sort,
      COST_TYPE_ADDRESS,
      grids?.[COST_TYPE_GRID_KEY]?.page_size,
    ),
    typeOffset: offsetOf(search.get(COST_TYPE_ADDRESS.offset)),
    kinds: readValues(search, COST_TYPE_KINDS, COST_TYPE_KIND_VALUES),
    typeState: state(COST_TYPE_STATE, COST_TYPE_GRID_KEY),
    categories: readGridQuery(
      search,
      COST_CATEGORY_SORTS,
      grids?.[COST_CATEGORY_GRID_KEY]?.sort,
      COST_CATEGORY_ADDRESS,
      grids?.[COST_CATEGORY_GRID_KEY]?.page_size,
    ),
    categoryOffset: offsetOf(search.get(COST_CATEGORY_ADDRESS.offset)),
    nature: identifierOf(search, CATEGORY_COST_TYPE),
    categoryState: state(CATEGORY_STATE, COST_CATEGORY_GRID_KEY),
  };
}

/**
 * Read the grid of the hourly rates, the natures and the categories of the pages the address asks,
 * each in the state its filter says, and every active nature, which the filter of the categories and
 * the form of a category offer — and, for a session that modifies the categories, every nature
 * deactivated ones included, whose types the form of a category compares (#577): a category under a
 * deactivated nature is offered the active natures of its type. Read only by a session that may
 * modify the settings (403 otherwise).
 */
async function readCosts(queries: CostQueries) {
  const client = serverClient();
  const { editable } = queries;
  return Promise.all([
    readOrRefused("getHourlyRateGrid", BOUNDS_REFUSED, () =>
      client.GET("/reference/hourly-rates", {
        params: {
          query: {
            ...asked(queries.rates, queries.rateOffset),
            ...stateQuery(queries.rateFilters.state, editable),
            ...rateBounds(queries.rateFilters),
          },
        },
      }),
    ),
    readOrFail("listCostTypes", () =>
      client.GET("/reference/cost-types", {
        params: {
          query: {
            ...asked(queries.types, queries.typeOffset),
            ...(queries.kinds.length === 0 ? {} : { kinds: [...queries.kinds] }),
            ...stateQuery(queries.typeState, editable),
          },
        },
      }),
    ),
    readOrFail("listCostCategories", () =>
      client.GET("/reference/cost-categories", {
        params: {
          query: {
            ...asked(queries.categories, queries.categoryOffset),
            ...given("cost_type_id", queries.nature),
            ...stateQuery(queries.categoryState, editable),
          },
        },
      }),
    ),
    readEveryPage("listCostTypes", (page) =>
      client.GET("/reference/cost-types", { params: { query: page } }),
    ),
    editable
      ? readEveryPage("listCostTypes", (page) =>
          client.GET("/reference/cost-types", {
            params: { query: { include_inactive: true, ...page } },
          }),
        )
      : undefined,
  ]);
}

/**
 * The title of the screen, the currency every amount of it is expressed in, and the link to the
 * correspondence of the actual costs.
 */
function CostsHeader({
  settings,
  writes,
}: {
  readonly settings: ReferenceSettings;
  /** Whether the session may modify the cost settings, and its commands write. */
  readonly writes: boolean;
}) {
  const t = useTranslations();
  return (
    <>
      <PageHeader
        title={t("functions.costSettings")}
        icon={FUNCTION_ICONS.cost_settings}
        density={FUNCTION_DENSITY.cost_settings}
        subtitle={t("reference.currency", { currency: settings.currency_code })}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <CommandTooltip
              label={t(MAPPING.label)}
              help={t("commands.openActualCostMapping.help")}
            >
              <Link
                href={MAPPING.route}
                className={buttonVariants({ variant: "outline", size: "sm" })}
              >
                <MappingIcon aria-hidden="true" />
                {t(MAPPING.label)}
              </Link>
            </CommandTooltip>
          </div>
        }
      />
      {writes ? (
        <CompanySettings settings={settings} />
      ) : (
        <CompanyName name={settings.company_name} />
      )}
    </>
  );
}

/**
 * What the filters of the grid of the rates offer of its reading: the years of the grid to bound the
 * rate of; the grid unread, its bounds refused, the year the address names, and the lower bound the
 * refusal names.
 */
function rateFiltered(
  rates: ReadOrRefused<HourlyRateGrid, ExpectedRefusal>,
  { year }: RateFilters,
): { readonly years: readonly number[]; readonly refused: RefusedBounds | undefined } {
  return rates.kind === "read"
    ? { years: rates.data.years, refused: undefined }
    : {
        years: year === undefined ? [] : [year],
        refused: refusedBounds(rates.problem.fields ?? []),
      };
}

/**
 * Every nature, deactivated ones included, each with its type, which the form of a category
 * compares; none for a session that does not write, which has no form.
 */
function typesOf(typed: readonly CostType[] | undefined): NatureChoice[] | undefined {
  return typed?.map(natureChoice);
}

/**
 * The card of the grid of the hourly rates, with its filters. It has no command at the right of its
 * title: the column of a year is added from the end of the bar of its grid (#3071, `RateGrid`).
 */
function RatesSection({ children }: { readonly children: ReactNode }) {
  const t = useTranslations("reference.rates");
  return (
    <ReferenceCard title={t("title")} icon={Coins}>
      {children}
    </ReferenceCard>
  );
}

/** Render the settings of the costs: the grid of the hourly rates, the natures, the categories. */
export default async function CostSettingsPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const [search, session] = await Promise.all([
    searchParams.then((asked) => pageSearch(asked)),
    requestSession(),
  ]);
  const permissions = session?.permissions ?? [];
  const grids = session?.display_preferences?.grids ?? undefined;
  const queries = readQueries(search, grids, permissions);
  const { editable } = queries;
  const [settings, [rates, types, categories, natures, typed]] = await Promise.all([
    readReferenceSettings(),
    readCosts(queries),
  ]);
  // The filters of the rates: in the bar of their grid, or above the sentence that stands for it.
  const rateBar = (
    <RateFilterBar
      filters={queries.rateFilters}
      editable={editable}
      {...rateFiltered(rates, queries.rateFilters)}
    />
  );
  return (
    <Screen density={FUNCTION_DENSITY.cost_settings}>
      <PendingAddress>
        <CostsHeader settings={settings} writes={editable} />
        <CostTypeList
          rows={types.items}
          page={types.meta}
          query={queries.types}
          preferences={grids?.[COST_TYPE_GRID_KEY] ?? undefined}
          state={queries.typeState}
          editable={editable}
          kinds={queries.kinds}
        />
        <CostCategoryList
          rows={categories.items}
          page={categories.meta}
          query={queries.categories}
          preferences={grids?.[COST_CATEGORY_GRID_KEY] ?? undefined}
          state={queries.categoryState}
          editable={editable}
          natures={natures.map(natureChoice)}
          every={typesOf(typed)}
          nature={queries.nature}
        />
        <RatesSection>
          {rates.kind === "read" ? (
            <RateGrid
              grid={rates.data}
              currency={settings.currency_code}
              editable={editable}
              query={queries.rates}
              preferences={grids?.[RATE_GRID_KEY] ?? undefined}
              filters={queries.rateFilters}
              panel={rateBar}
            />
          ) : (
            <>
              {rateBar}
              <BoundsRefused />
            </>
          )}
        </RatesSection>
      </PendingAddress>
    </Screen>
  );
}
