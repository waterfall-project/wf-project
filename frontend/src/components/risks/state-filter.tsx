// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of the risks by state (WF-RIS-0040), the filter of a list on the values of a column
 * (`ValuesFilter`): a button for each state of the contract, and one for every state. A state chosen
 * only changes the address (`states`, as the contract names it); the page reads the risks anew,
 * which the server filters, with the totals of those it retained (WF-IHM-0130).
 */
"use client";

import { useTranslations } from "next-intl";

import { ValuesFilter } from "@/components/grid/values-filter";

import { RISK_STATES, type RiskState, STATES } from "./address";

/** Render the filter of the risks by state, the states the address filters on pressed. */
export function RiskStateFilter({ states }: { readonly states: readonly RiskState[] }) {
  const t = useTranslations();
  return (
    <ValuesFilter
      name={STATES}
      label={t("risks.filter")}
      every={t("risks.everyState")}
      values={RISK_STATES.map((state) => ({ value: state, text: t(`enums.RiskState.${state}`) }))}
      chosen={states}
    />
  );
}
