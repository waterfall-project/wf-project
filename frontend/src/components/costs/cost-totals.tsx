// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the consultation of the actual costs says above its list: the total of the tracked scope,
 * the total excluded and the general total, of every line the filters retained — not of the page
 * shown —, each as the server gives it (WF-CRE-0040, WF-ARC-0020) and marked computed; and the
 * date of the last import, from which the figures read date (WF-CRE-0050), in the local time of
 * the workstation, or that nothing has been imported yet.
 */
import { useTranslations } from "next-intl";

import { LocalTime } from "@/components/local-time";
import { ComputedTotal } from "@/components/computed-amount";

import type { ActualCostTotals } from "./cost-grid";

/** The three totals, in the order of the requirement. */
const TOTALS = [
  "tracked",
  "excluded",
  "overall",
] as const satisfies readonly (keyof ActualCostTotals)[];

/** Render the three totals of the lines retained, and the date of the last import. */
export function CostSummary({
  totals,
  lastImport,
}: {
  readonly totals: ActualCostTotals;
  readonly lastImport: string | null | undefined;
}) {
  const t = useTranslations("actualCosts");
  return (
    <section aria-label={t("totals.title")}>
      <dl className="flex flex-wrap gap-x-8 gap-y-2">
        {TOTALS.map((total) => (
          <ComputedTotal key={total} name={t(`totals.${total}`)} amount={totals[total]} />
        ))}
        <div className="space-y-0.5">
          <dt className="text-xs text-muted-foreground">{t("lastImport.label")}</dt>
          <dd className="font-semibold">
            {lastImport === null || lastImport === undefined ? (
              t("lastImport.never")
            ) : (
              <LocalTime value={lastImport} />
            )}
          </dd>
        </div>
      </dl>
    </section>
  );
}
