// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * An indicator as the API computes it, with the date it is computed at (WF-IHM-0020): a value
 * under the envelope `Computable` never shows without the date of its `CalculationContext`,
 * in the local time of the workstation. A value that cannot be computed shows as such, with
 * the reason the API gives — never as zero nor as infinity (WF-IND-0010), and never as a
 * value the front would make up.
 */
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { LocalTime } from "@/components/local-time";
import { formatDecimal } from "@/i18n/format";

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

/** An indicator: its name, in the language of the interface; its value; its context. */
export interface ComputedIndicatorProps {
  readonly label: string;
  readonly value: Computable;
  readonly context: CalculationContext;
}

/** Render an indicator, its value or why it has none, and the date it is computed at. */
export function ComputedIndicator({ label, value, context }: ComputedIndicatorProps) {
  const t = useTranslations();
  const locale = useLocale();
  // A value the API calls computable yet leaves out is not made up either: it is said missing.
  const computed = value.is_computable ? (value.value ?? null) : null;
  const reason = computed === null ? (value.reason ?? "") : "";
  return (
    <dl className="space-y-0.5">
      <dt className="text-sm text-muted-foreground">{label}</dt>
      <dd className="text-lg font-semibold tabular-nums">
        {computed === null ? t("indicator.notComputable") : formatDecimal(computed, locale)}
      </dd>
      {reason === "" ? null : <dd className="text-sm text-muted-foreground">{reason}</dd>}
      <dd>
        <CalculationDate context={context} />
      </dd>
    </dl>
  );
}
