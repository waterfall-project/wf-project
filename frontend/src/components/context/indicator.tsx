// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * An indicator as the API computes it, with the date it is computed at (WF-IHM-0020): a value
 * under the envelope `Computable` never shows without the date of its `CalculationContext`,
 * in the local time of the workstation. A value that cannot be computed shows as such, with
 * the reason the API codes, in the sentence of the catalogue — never as zero nor as infinity
 * (WF-IND-0010), and never as a value the front would make up.
 */
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { LocalTime } from "@/components/local-time";
import type { Catalogue } from "@/i18n/catalogues";
import { formatDecimal, formatShare } from "@/i18n/format";

/** A value that may not be computable (WF-IND-0010). */
export type Computable = components["schemas"]["Computable"];

/** The context an indicator is computed in: its revision, its date, its scope. */
export type CalculationContext = components["schemas"]["CalculationContext"];

/** The context of a calculation, whose date an indicator shows. */
export interface CalculationDateProps {
  readonly context: CalculationContext;
}

/** Render the date an indicator is computed at, in the local time of the workstation. */
export function CalculationDate({ context }: CalculationDateProps) {
  const t = useTranslations();
  return (
    <span className="text-xs text-muted-foreground">
      {t.rich("indicator.computedAt", {
        time: () => <LocalTime value={context.computed_at} />,
      })}
    </span>
  );
}

/** The name of an indicator whose value may not be computable. */
type IndicatorName = keyof Catalogue["indicator"]["names"];

/** The key of the label of an indicator in the catalogues. */
export type IndicatorLabel = `indicator.names.${IndicatorName}`;

/**
 * How each indicator shows its value: a progress or a consumption is a share, a percentage to
 * the hundredth; an index or a projection, as the decimal the API gave. Every name of the
 * catalogue is classified: one added there fails the type check until it is here.
 */
const FORMATS: Readonly<Record<IndicatorLabel, typeof formatShare>> = {
  "indicator.names.financialProgress": formatShare,
  "indicator.names.budgetConsumption": formatShare,
  "indicator.names.physicalProgress": formatShare,
  "indicator.names.costIndex": formatDecimal,
  "indicator.names.scheduleIndex": formatDecimal,
  "indicator.names.projectionAtObservedRate": formatDecimal,
};

/** An indicator: the key of its name in the catalogues; its value; its context. */
export interface ComputedIndicatorProps {
  readonly indicator: IndicatorLabel;
  readonly value: Computable;
  readonly context: CalculationContext;
  /**
   * Where the date of its context shows: under the value (`own`, the default), or above it, by
   * the card or the section that holds the indicator and shows the date of the same context
   * (`held`) — once for all its indicators, never left out.
   */
  readonly date?: "own" | "held";
}

/** Render an indicator, its value or why it has none, and the date it is computed at. */
export function ComputedIndicator({
  indicator,
  value,
  context,
  date = "own",
}: ComputedIndicatorProps) {
  const t = useTranslations();
  const bounds = useTranslations("share");
  const locale = useLocale();
  // A value the API calls computable yet leaves out is not made up either: it is said missing.
  const computed = value.is_computable ? (value.value ?? null) : null;
  const reason = computed === null ? (value.reason ?? null) : null;
  return (
    <dl className="space-y-0.5">
      <dt className="text-sm text-muted-foreground">{t(indicator)}</dt>
      <dd className="text-lg font-semibold tabular-nums">
        {computed === null
          ? t("indicator.notComputable")
          : FORMATS[indicator](computed, locale, bounds)}
      </dd>
      {reason === null ? null : (
        <dd className="text-sm text-muted-foreground">
          {t(`enums.NotComputableReason.${reason}`)}
        </dd>
      )}
      {date === "own" ? (
        <dd>
          <CalculationDate context={context} />
        </dd>
      ) : null}
    </dl>
  );
}
