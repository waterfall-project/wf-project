// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a grid of the structure on the nodes a risk occurred merged (WF-RIS-0060,
 * WF-IHM-0130), above the grid of the planning and of the estimate: one list of the browser, « Issues
 * d'un risque » for the nodes of any risk, then the risks occurred of the project, each by its label,
 * and one choice that lifts the filter (`ChoiceFilter`). The first writes `is_from_risk`, a risk
 * `origin_risk_ids`, the other lifted; the page reads the grid anew, which the server filters. A
 * risk the address names that the project does not list as occurred stays chosen, under its
 * identifier, to be cleared.
 *
 * Neither server nor client of its own: the page that renders it hands it data.
 */
import { useTranslations } from "next-intl";

import { ChoiceFilter } from "./choice-filter";
import {
  ORIGIN_ANY_PARAMETER,
  ORIGIN_ANY_VALUE,
  ORIGIN_RISK_PARAMETER,
  type OriginChoices,
  type OriginFilter,
} from "./origin-filter";

/** The value of the list the filter stands for; none, no filter. */
function chosenOf(filter: OriginFilter | undefined): string | undefined {
  if (filter === undefined) {
    return undefined;
  }
  return filter.kind === "any" ? ORIGIN_ANY_VALUE : filter.risk;
}

/** Render the filter of a grid on the nodes of a risk occurred, the one the address names chosen. */
export function OriginFilterChoice({ choices }: { readonly choices: OriginChoices }) {
  const t = useTranslations("grid.originFilter");
  return (
    <ChoiceFilter
      name={ORIGIN_ANY_PARAMETER}
      label={t("label")}
      every={t("every")}
      choices={[
        { value: ORIGIN_ANY_VALUE, text: t("any"), name: ORIGIN_ANY_PARAMETER },
        ...choices.risks.map((risk) => ({
          value: risk.id,
          text: risk.label,
          name: ORIGIN_RISK_PARAMETER,
        })),
      ]}
      chosen={chosenOf(choices.filter)}
    />
  );
}
