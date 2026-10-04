// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The settings of the costs (FBS-3.1, US-0250), outside any project: the currency of the
 * installation, every amount expressed in it (WF-REF-0140); the grid of the hourly rates, a row for
 * each category of labour and a column for each year, on the dense grid, searched by the server as
 * the address asks (`search`), its cells entered where the session may modify the cost settings
 * (FBS-3.1.2, WF-REF-0050); and, beside it, the natures and the categories of cost (FBS-3.1.1).
 * Every figure as the API gives it: the front computes, sorts and filters nothing. A read the API
 * refuses, or cannot answer, is thrown for the pages of the shell to say.
 */
import type { Metadata } from "next";
import { useTranslations } from "next-intl";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { platformOffer } from "@/components/commands/offer";
import { type GridQuery, readGridQuery } from "@/components/grid/query";
import { CostCategoryList, CostTypeList } from "@/components/reference/cost-lists";
import { RATE_GRID_KEY, RateGrid } from "@/components/reference/rate-grid";
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

/** The grid of the hourly rates, the categories retained by the search the address asks. */
async function readRates({ search }: GridQuery<never>) {
  return readOrFail("getHourlyRateGrid", () =>
    serverClient().GET("/reference/hourly-rates", {
      params: { query: search === undefined ? {} : { search } },
    }),
  );
}

/** The natures of cost, and the categories attached to them. */
async function readCosts() {
  const client = serverClient();
  return Promise.all([
    readOrFail("listCostTypes", () => client.GET("/reference/cost-types")),
    readOrFail("listCostCategories", () => client.GET("/reference/cost-categories")),
  ]);
}

/** The title of the screen, and the currency every amount of it is expressed in. */
function CostsHeader({ currency }: { readonly currency: string }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.costSettings")}
      icon={FUNCTION_ICONS.cost_settings}
      density={FUNCTION_DENSITY.cost_settings}
      subtitle={t("reference.currency", { currency })}
    />
  );
}

/** Render the settings of the costs: the grid of the hourly rates, the natures, the categories. */
export default async function CostSettingsPage({
  searchParams,
}: {
  searchParams: Promise<PageSearchParams>;
}) {
  const query = readGridQuery<never>(pageSearch(await searchParams), []);
  const [settings, rates, [types, categories], session] = await Promise.all([
    readReferenceSettings(),
    readRates(query),
    readCosts(),
    requestSession(),
  ]);
  return (
    <Screen density={FUNCTION_DENSITY.cost_settings} fill>
      <CostsHeader currency={settings.currency_code} />
      <div className="flex min-h-0 flex-1 flex-col gap-4 lg:flex-row">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col">
          <RateGrid
            grid={rates}
            currency={settings.currency_code}
            editable={platformOffer(session?.permissions, "cost_settings") !== undefined}
            query={query}
            preferences={session?.user.display_preferences?.grids?.[RATE_GRID_KEY] ?? undefined}
          />
        </div>
        <aside className="flex shrink-0 flex-col gap-4 lg:w-[28rem] lg:overflow-y-auto">
          <CostTypeList types={types} />
          <CostCategoryList categories={categories} types={types} />
        </aside>
      </div>
    </Screen>
  );
}
