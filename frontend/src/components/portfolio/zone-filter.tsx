// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of the list of the projects of the portfolio by the zone of their indices (#313,
 * WF-IHM-0130), the filter of a list on the values of a column (`ValuesFilter`): a button for each
 * zone of the contract, named by the one signal of the application (WF-IHM-0070), and one for every
 * zone. A zone chosen only changes the address (`zones`, as the contract names it), back to the
 * first page; the page reads the projects anew, which the server retains when their cost index or
 * their schedule index is in one of the zones, with their number (`meta.total`). Every zone chosen
 * still filters: a project without an index is in none.
 */
"use client";

import { useTranslations } from "next-intl";

import { OFFSET } from "@/components/grid/query";
import { ValuesFilter } from "@/components/grid/values-filter";
import { Signal } from "@/components/signal/signal";

import { type AlertZone, INDEX_ZONES, ZONES } from "./address";

/** Render the filter of the projects by the zone of their indices, the zones asked pressed. */
export function ZoneFilter({ zones }: { readonly zones: readonly AlertZone[] }) {
  const t = useTranslations("portfolio.projects");
  return (
    <ValuesFilter
      name={ZONES}
      label={t("zones")}
      every={t("everyZone")}
      values={INDEX_ZONES.map((zone) => ({ value: zone, text: <Signal zone={zone} /> }))}
      chosen={zones}
      page={OFFSET}
      exhaustive={false}
      shaded
    />
  );
}
