// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The perimeter a view of the portfolio is computed on, in words: the sentence its header shows
 * under its title, and the provenance the exported image of its charts names (WF-IHM-0130, #312)
 * — a view of the portfolio has neither a project nor a revision to name, but the states, the
 * period and the node of organisation the server retained, and the date of calculation,
 * `scope.as_of`, as the server gives them. Nothing of it is deduced from the address.
 */
import { useFormatter, useLocale, useTranslations } from "next-intl";

import type { ChartExport } from "@/components/chart/chart";
import { formatPlanningDate } from "@/i18n/format";

import type { PortfolioScope } from "./address";

/**
 * The perimeter the server retained, in a sentence: states, projects, period, date of
 * calculation — a date of planning, shown without time zone.
 */
export function useScopeSentence(): (scope: PortfolioScope) => string {
  const t = useTranslations("portfolio.scope");
  const enums = useTranslations("enums.ProjectState");
  const format = useFormatter();
  const locale = useLocale();
  return (scope: PortfolioScope) => {
    const date = (value: string) => formatPlanningDate(value, locale);
    const states = format.list(scope.states.map((state) => enums(state)));
    const asOf = date(scope.as_of);
    const from = scope.from ?? null;
    const to = scope.to ?? null;
    const count = scope.project_count;
    if (from !== null && to !== null) {
      return t("period", { states, count, asOf, from: date(from), to: date(to) });
    }
    if (from !== null) {
      return t("since", { states, count, asOf, from: date(from) });
    }
    if (to !== null) {
      return t("until", { states, count, asOf, to: date(to) });
    }
    return t("noPeriod", { states, count, asOf });
  };
}

/**
 * What the exported image of a chart of the portfolio says of itself: its title — which names the
 * portfolio —, then the perimeter the server retained and its date of calculation, and the node
 * of organisation when there is one; and the name of its file, `file` followed by the date of
 * calculation.
 */
export function usePortfolioExport(
  scope: PortfolioScope,
  title: string,
  file: string,
): () => ChartExport {
  const t = useTranslations("chart");
  const node = useTranslations("portfolio.scope");
  const sentence = useScopeSentence();
  return () => {
    const perimeter = sentence(scope);
    return {
      title,
      subtitle:
        scope.org_node_label === null
          ? perimeter
          : t("exportPortfolioSubtitleWith", {
              scope: perimeter,
              node: node("node", { node: scope.org_node_label }),
            }),
      fileName: t("portfolioFileName", { file, asOf: scope.as_of }),
    };
  };
}
