// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the costs (FBS-3.1, US-0250), outside any project: the currency of the
 * installation, every amount expressed in it (WF-REF-0140), and beside it the name of the company the
 * exported files bear (WF-EXP-0020), modified where the session may modify the cost settings; then, stacked one under the other in a
 * page that scrolls, as the settings of the resources are (US-0570, #1044), the natures and the
 * categories of cost (FBS-3.1.1), two dense grids searched, filtered, sorted and paged by the
 * server, as the address asks under the names of each grid (#510), and the grid of the hourly rates
 * (FBS-3.1.2), a row for each category of labour and a column for each year, on the dense grid,
 * searched, filtered on the state of its categories and on the bounds of the rate of a year, sorted
 * and paged by the server under the names of the contract (#509, #545), its cells entered where the
 * session may modify the cost settings (WF-REF-0050). Each grid keeps a height of its own, no taller
 * than the window; its size is the rows per page the account chose for it (WF-IHM-0060). Every
 * figure as the API gives it: the front computes, sorts, filters and pages nothing.
 *
 * The lists and the grid hold the active objects alone, and the deactivated ones too when the
 * address asks for them and the session bears the permission of reading of the cost settings,
 * without which the contract refuses `include_inactive` (WF-REF-0150, 403); each nature and each
 * category carries the command that reactivates it, as the server lists it. The categories are
 * filtered by a nature chosen among every one the session reads, read whole as a list of choices is
 * (#303). A session that may modify the cost settings creates and modifies the natures and the
 * categories, and deactivates them as each lists it (EP-02/L43a), the form of a category reading the
 * type of every nature, deactivated ones included (EP-02/L42g); the screen then says that the fake
 * back keeps none of what is written (`MockupNotice`). Bounds of the rate the API refuses (422) leave the grid unread, the bound said at its
 * field; any other read the API refuses, or cannot answer, is thrown for the pages of the shell to
 * say.
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
  asksInactive,
  given,
  identifierOf,
  inactiveQuery,
  type KeptGrids,
  stateOf,
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
import { InactiveSwitch } from "@/components/reference/reference-filters";
import { CompanyName, CompanySettings } from "@/components/reference/settings-forms";
import { BoundsRefused, ReferenceSection } from "@/components/reference/section";
import { FUNCTION_DENSITY, FUNCTION_ICONS, LEAF_ICONS } from "@/components/shell/function-display";
import { MockupNotice } from "@/components/shell/mockup-notice";
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

/** The pages of the lists the server pages, which the switch of the deactivated objects resets. */
const PAGES = [
  CONTRACT_ADDRESS.offset,
  COST_TYPE_ADDRESS.offset,
  COST_CATEGORY_ADDRESS.offset,
] as const;

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
  readonly inactive: { readonly include_inactive?: true };
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
  const state = (name: string) => stateOf(search, name, permissions, "cost_settings.read");
  return {
    inactive: inactiveQuery(asksInactive(search), permissions, "cost_settings.read"),
    rates: readGridQuery(
      search,
      RATE_SORTS,
      grids?.[RATE_GRID_KEY]?.sort,
      CONTRACT_ADDRESS,
      grids?.[RATE_GRID_KEY]?.page_size,
    ),
    rateOffset: offsetOf(search.get(CONTRACT_ADDRESS.offset)),
    rateFilters: readRateFilters(search, state(RATE_STATE)),
    types: readGridQuery(
      search,
      COST_TYPE_SORTS,
      grids?.[COST_TYPE_GRID_KEY]?.sort,
      COST_TYPE_ADDRESS,
      grids?.[COST_TYPE_GRID_KEY]?.page_size,
    ),
    typeOffset: offsetOf(search.get(COST_TYPE_ADDRESS.offset)),
    kinds: readValues(search, COST_TYPE_KINDS, COST_TYPE_KIND_VALUES),
    typeState: state(COST_TYPE_STATE),
    categories: readGridQuery(
      search,
      COST_CATEGORY_SORTS,
      grids?.[COST_CATEGORY_GRID_KEY]?.sort,
      COST_CATEGORY_ADDRESS,
      grids?.[COST_CATEGORY_GRID_KEY]?.page_size,
    ),
    categoryOffset: offsetOf(search.get(COST_CATEGORY_ADDRESS.offset)),
    nature: identifierOf(search, CATEGORY_COST_TYPE),
    categoryState: state(CATEGORY_STATE),
  };
}

/**
 * Read the grid of the hourly rates, the natures and the categories of the pages the address asks,
 * and every nature, which the filter of the categories offers — and, for a session that modifies the
 * categories, every nature deactivated ones included, whose types the form of a category
 * compares (#577): a category under a deactivated nature is offered the active natures of its type.
 * Read only when the natures the filter offers leave the deactivated ones out, and only by a session
 * that may read them (403 otherwise).
 */
async function readCosts(
  queries: CostQueries,
  session: { readonly editable: boolean; readonly readsInactive: boolean },
) {
  const client = serverClient();
  const { inactive } = queries;
  const typing = session.editable && session.readsInactive && inactive.include_inactive !== true;
  return Promise.all([
    readOrRefused("getHourlyRateGrid", BOUNDS_REFUSED, () =>
      client.GET("/reference/hourly-rates", {
        params: {
          query: {
            ...inactive,
            ...asked(queries.rates, queries.rateOffset),
            ...given("is_active", queries.rateFilters.state),
            ...rateBounds(queries.rateFilters),
          },
        },
      }),
    ),
    readOrFail("listCostTypes", () =>
      client.GET("/reference/cost-types", {
        params: {
          query: {
            ...inactive,
            ...asked(queries.types, queries.typeOffset),
            ...(queries.kinds.length === 0 ? {} : { kinds: [...queries.kinds] }),
            ...given("is_active", queries.typeState),
          },
        },
      }),
    ),
    readOrFail("listCostCategories", () =>
      client.GET("/reference/cost-categories", {
        params: {
          query: {
            ...inactive,
            ...asked(queries.categories, queries.categoryOffset),
            ...given("cost_type_id", queries.nature),
            ...given("is_active", queries.categoryState),
          },
        },
      }),
    ),
    readEveryPage("listCostTypes", (page) =>
      client.GET("/reference/cost-types", { params: { query: { ...inactive, ...page } } }),
    ),
    typing
      ? readEveryPage("listCostTypes", (page) =>
          client.GET("/reference/cost-types", {
            params: { query: { include_inactive: true, ...page } },
          }),
        )
      : undefined,
  ]);
}

/**
 * The title of the screen, the currency every amount of it is expressed in, and the switch of the
 * deactivated objects for who may read them; under it, for who may write, that the fake back keeps
 * nothing of what is written.
 */
function CostsHeader({
  settings,
  inactive,
  writes,
}: {
  readonly settings: ReferenceSettings;
  readonly inactive: boolean | undefined;
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
            {inactive === undefined ? null : <InactiveSwitch shown={inactive} pages={PAGES} />}
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
      {writes ? <MockupNotice /> : null}
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
 * Every nature, each with its type, which the form of a category compares: those read with the
 * deactivated ones, or those the filter offers when they were not read apart; none for a session
 * that does not write, which has no form.
 */
function typesOf(
  editable: boolean,
  typed: readonly CostType[] | undefined,
  natures: readonly CostType[],
): NatureChoice[] | undefined {
  return editable ? (typed ?? natures).map(natureChoice) : undefined;
}

/** The section of the grid of the hourly rates, under its title, with its filters. */
function RatesSection({ children }: { readonly children: ReactNode }) {
  const t = useTranslations("reference.rates");
  return (
    <ReferenceSection title={t("title")} icon={Coins}>
      {children}
    </ReferenceSection>
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
  const editable = platformOffer(permissions, "cost_settings") !== undefined;
  const readsInactive = permissions.includes("cost_settings.read");
  const [settings, [rates, types, categories, natures, typed]] = await Promise.all([
    readReferenceSettings(),
    readCosts(queries, { editable, readsInactive }),
  ]);
  return (
    <Screen density={FUNCTION_DENSITY.cost_settings}>
      <PendingAddress>
        <CostsHeader
          settings={settings}
          inactive={readsInactive ? queries.inactive.include_inactive === true : undefined}
          writes={editable}
        />
        <CostTypeList
          rows={types.items}
          page={types.meta}
          query={queries.types}
          preferences={grids?.[COST_TYPE_GRID_KEY] ?? undefined}
          state={queries.typeState}
          readsInactive={readsInactive}
          editable={editable}
          kinds={queries.kinds}
        />
        <CostCategoryList
          rows={categories.items}
          page={categories.meta}
          query={queries.categories}
          preferences={grids?.[COST_CATEGORY_GRID_KEY] ?? undefined}
          state={queries.categoryState}
          readsInactive={readsInactive}
          editable={editable}
          natures={natures.map(natureChoice)}
          every={typesOf(editable, typed, natures)}
          nature={queries.nature}
        />
        <RatesSection>
          <RateFilterBar
            filters={queries.rateFilters}
            readsInactive={readsInactive}
            {...rateFiltered(rates, queries.rateFilters)}
          />
          {rates.kind === "read" ? (
            <RateGrid
              grid={rates.data}
              currency={settings.currency_code}
              editable={editable}
              query={queries.rates}
              preferences={grids?.[RATE_GRID_KEY] ?? undefined}
            />
          ) : (
            <BoundsRefused />
          )}
        </RatesSection>
      </PendingAddress>
    </Screen>
  );
}
