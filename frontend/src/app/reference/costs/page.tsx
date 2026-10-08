// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the costs (FBS-3.1, US-0250), outside any project: the currency of the
 * installation, every amount expressed in it (WF-REF-0140); the grid of the hourly rates, a row for
 * each category of labour and a column for each year, on the dense grid, searched by the server as
 * the address asks (`search`), its cells entered where the session may modify the cost settings
 * (FBS-3.1.2, WF-REF-0050); and, beside it, the natures and the categories of cost (FBS-3.1.1).
 * Every figure as the API gives it: the front computes, sorts and filters nothing.
 *
 * The lists and the grid hold the active objects alone, and the deactivated ones too when the
 * address asks for them and the session bears the permission of reading of the cost settings,
 * without which the contract refuses `include_inactive` (WF-REF-0150, 403); a session that may
 * modify the cost settings reactivates a nature or a category. A read the API refuses, or cannot
 * answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { platformOffer } from "@/components/commands/offer";
import { PendingAddress } from "@/components/grid/pending-address";
import { type GridQuery, readGridQuery } from "@/components/grid/query";
import { asksInactive, inactiveQuery } from "@/components/reference/address";
import { CostCategoryList, CostTypeList } from "@/components/reference/cost-lists";
import { RATE_GRID_KEY, RateGrid } from "@/components/reference/rate-grid";
import { InactiveSwitch } from "@/components/reference/reference-filters";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import { type PageSearchParams, pageSearch } from "@/navigation/context";
import { requestSession } from "@/session/request";

import { screenMetadata } from "../../title";
import { readReferenceSettings } from "../settings";

/** Title the tab with the function. */
export async function generateMetadata(): Promise<Metadata> {
  return screenMetadata("functions.costSettings");
}

/** What the lists ask of the deactivated objects: them too, or nothing. */
interface Inactive {
  readonly include_inactive?: true;
}

/** The grid of the hourly rates, the categories retained by the search the address asks. */
async function readRates({ search }: GridQuery<never>, inactive: Inactive) {
  return readOrFail("getHourlyRateGrid", () =>
    serverClient().GET("/reference/hourly-rates", {
      params: { query: { ...inactive, ...(search === undefined ? {} : { search }) } },
    }),
  );
}

/** The natures of cost, and the categories attached to them. */
async function readCosts(inactive: Inactive) {
  const client = serverClient();
  const query = { params: { query: { ...inactive } } };
  return Promise.all([
    readOrFail("listCostTypes", () => client.GET("/reference/cost-types", query)),
    readOrFail("listCostCategories", () => client.GET("/reference/cost-categories", query)),
  ]);
}

/**
 * The title of the screen, the currency every amount of it is expressed in, and the switch of the
 * deactivated objects for who may read them.
 */
function CostsHeader({
  currency,
  inactive,
}: {
  readonly currency: string;
  readonly inactive: boolean | undefined;
}) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.costSettings")}
      icon={FUNCTION_ICONS.cost_settings}
      density={FUNCTION_DENSITY.cost_settings}
      subtitle={t("reference.currency", { currency })}
      actions={inactive === undefined ? undefined : <InactiveSwitch shown={inactive} />}
    />
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
  const query = readGridQuery<never>(search, []);
  const inactive = inactiveQuery(asksInactive(search), permissions, "cost_settings.read");
  const [settings, rates, [types, categories]] = await Promise.all([
    readReferenceSettings(),
    readRates(query, inactive),
    readCosts(inactive),
  ]);
  const editable = platformOffer(permissions, "cost_settings") !== undefined;
  return (
    <Screen density={FUNCTION_DENSITY.cost_settings} fillWide>
      <PendingAddress>
        <CostsHeader
          currency={settings.currency_code}
          inactive={
            permissions.includes("cost_settings.read")
              ? inactive.include_inactive === true
              : undefined
          }
        />
        <div className="flex flex-col gap-4 lg:min-h-0 lg:flex-1 lg:flex-row">
          <div className="flex min-w-0 flex-col lg:min-h-0 lg:flex-1">
            <RateGrid
              grid={rates}
              currency={settings.currency_code}
              editable={editable}
              query={query}
              preferences={session?.user.display_preferences?.grids?.[RATE_GRID_KEY] ?? undefined}
            />
          </div>
          <aside className="flex shrink-0 flex-col gap-4 lg:w-[28rem] lg:overflow-y-auto">
            <CostTypeList types={types} reactivable={editable} />
            <CostCategoryList categories={categories} reactivable={editable} />
          </aside>
        </div>
      </PendingAddress>
    </Screen>
  );
}
