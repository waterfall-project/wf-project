// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The filter of a grid of the structure by a lot or by a post (WF-PLA-0080, WF-DEV-0050), above the
 * grid of the planning and of the estimate: one list of the browser, the lots and the posts of the
 * work breakdown read whole in its order, each named by its kind and its label — a lot, then its
 * posts —, and one choice that lifts the filter (`ChoiceFilter`). A lot chosen writes
 * `work_package_id`, a post `order_item_id`, the other lifted; the page reads the grid anew, which
 * the server filters. An item the address names that the work breakdown does not have stays chosen,
 * under its identifier, to be cleared.
 *
 * Neither server nor client of its own: the page that renders it hands it data, and the list is
 * the browser's (`ChoiceFilter`).
 */
import { useTranslations } from "next-intl";

import { BREAKDOWN_PARAMETERS, type BreakdownChoices } from "./breakdown-filter";
import { ChoiceFilter } from "./choice-filter";

/** Render the filter of a grid by a lot or a post, the one the address names chosen. */
export function BreakdownFilterChoice({ choices }: { readonly choices: BreakdownChoices }) {
  const t = useTranslations("grid.breakdownFilter");
  return (
    <ChoiceFilter
      name={BREAKDOWN_PARAMETERS.work_package}
      label={t("label")}
      every={t("every")}
      choices={choices.items.map((item) => ({
        value: item.id,
        text: t("choice", { kind: item.kind, label: item.label }),
        name: BREAKDOWN_PARAMETERS[item.kind],
      }))}
      chosen={choices.filter?.value}
    />
  );
}
