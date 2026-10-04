// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The risk matrix of the revision read (WF-RIS-0040, WF-REF-0160): four levels of probability and
 * four of severity, each named by its bounds as the server gives them — the probability in percent,
 * the severity in percent of the reference budget —, and in each cell the zone the server classes
 * it in, by the one signal of the application (WF-IHM-0070), with the number of risks in it. The
 * front deduces no zone, counts no risk: it places each cell the answer gives by its two levels.
 * The highest probability is drawn at the top, as a matrix of risks reads.
 */
import { Grid2x2 } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { ICON } from "@/components/projects/project-tables";
import { Signal } from "@/components/signal/signal";
import { formatPercent } from "@/i18n/format";

/** The matrix, as the contract gives it. */
export type RiskMatrix = components["schemas"]["RiskMatrix"];

/** A level of an axis of the matrix, and its bounds. */
type Level = components["schemas"]["RiskMatrixLevel"];

/** The name of a level of an axis: its bounds, the upper one excluded, the last level unbounded. */
function useLevelName() {
  const t = useTranslations("risks.matrix");
  const locale = useLocale();
  return ({ lower, upper }: Level) =>
    upper === null
      ? t("from", { lower: formatPercent(lower, locale) })
      : t("between", { lower: formatPercent(lower, locale), upper: formatPercent(upper, locale) });
}

/** Render the risk matrix, its axes named by their bounds, each cell by its signal and its count. */
export function RiskMatrixView({ matrix }: { readonly matrix: RiskMatrix }) {
  const t = useTranslations("risks.matrix");
  const name = useLevelName();
  const cellAt = (probability: number, severity: number) =>
    matrix.cells.find(
      (cell) => cell.probability_level === probability && cell.severity_level === severity,
    );
  return (
    // One name, the caption's: the table is named by the title it bears.
    <table className="w-full table-fixed border-collapse text-xs">
      <caption className="pb-2 text-left">
        <h2 className="flex items-center gap-2 text-base font-semibold">
          <Grid2x2 aria-hidden="true" className={ICON} />
          {t("title")}
        </h2>
      </caption>
      <thead>
        <tr>
          <th scope="col" className="w-24 p-1 text-left align-bottom font-medium">
            {t("probability")}
          </th>
          <th scope="colgroup" colSpan={matrix.severity_levels.length} className="p-1 font-medium">
            {t("severity")}
          </th>
        </tr>
        <tr>
          <td />
          {matrix.severity_levels.map((level) => (
            <th key={level.level} scope="col" className="p-1 font-normal text-muted-foreground">
              {name(level)}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {[...matrix.probability_levels].reverse().map((probability) => (
          <tr key={probability.level}>
            <th scope="row" className="p-1 text-left font-normal text-muted-foreground">
              {name(probability)}
            </th>
            {matrix.severity_levels.map((severity) => {
              const cell = cellAt(probability.level, severity.level);
              return (
                <td key={severity.level} className="border p-1 text-center">
                  {cell === undefined ? null : (
                    <span className="inline-flex items-center gap-1 tabular-nums">
                      <Signal zone={cell.zone} variant="icon" />
                      {cell.count}
                    </span>
                  )}
                </td>
              );
            })}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
