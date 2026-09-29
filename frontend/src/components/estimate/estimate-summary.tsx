// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the estimate says above its grid: the hourly rates missing for its
 * calculation (WF-DEV-0010), each category named with its year, and the way to the reference
 * where rates are entered when the session may read it; then the indicators of the estimate
 * (WF-DEV-0060) — its total, its provisions, its deviation from the previous marked revision,
 * the one the contract gives (#160), its totals by nature of cost, in amount and in share of
 * the total, and by sub-project —, with the date they are computed at (WF-IHM-0020), or that
 * they are unavailable when the API did not give them.
 *
 * Every figure is the API's, formatted in the language of the interface from its exact string:
 * nothing is summed, nor divided, nor hidden by a rule of the front (WF-ARC-0020). A deviation
 * the API does not give is not shown as zero: it is left out. A name the API leaves out is said
 * missing, never replaced by an identifier.
 */
import { TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import { useId } from "react";

import { FUNCTION_ICONS } from "@/components/shell/function-display";

import type { components, operations } from "@/api/generated/schema";
import { CalculationDate } from "@/components/context/indicator";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { formatMoney, formatPercent } from "@/i18n/format";
import { functionOf } from "@/navigation/functions";

/** The indicators of an estimate, as the API computes them. */
export type EstimateIndicators = components["schemas"]["EstimateIndicators"];

/** The categories and years whose hourly rate the calculation of an estimate lacks. */
export type MissingRates =
  operations["getMissingRates"]["responses"][200]["content"]["application/json"];

/** A permission of the catalogue (WF-ADM-0100). */
type Permission = components["schemas"]["PermissionCode"];

/** An amount by key: a nature of cost, a sub-project. */
type AmountByKey = components["schemas"]["AmountByKey"];

/** The key the API gives the whole of what belongs to no sub-project (WF-IND-0020). */
const UNASSIGNED = "unassigned";

/** What the screen of the estimate says above its grid. */
export interface EstimateSummaryProps {
  /** The indicators, if the API gave them. */
  readonly indicators: EstimateIndicators | undefined;
  readonly missingRates: MissingRates;
  /** The permissions of the session: the reference is offered to one that may read it. */
  readonly permissions: readonly Permission[];
}

/**
 * Name the rates the calculation lacks, each category with its year, and lead to the function
 * of the reference where they are entered when the session may read it — to enter them if it
 * may write it, to see them otherwise —; nothing when none is missing.
 */
function MissingRatesNotice({
  missingRates,
  permissions,
}: Pick<EstimateSummaryProps, "missingRates" | "permissions">) {
  const t = useTranslations("estimateSummary");
  if (missingRates.length === 0) {
    return null;
  }
  const rates = functionOf("cost_settings");
  const Icon = FUNCTION_ICONS[rates.permission];
  return (
    <Alert>
      <TriangleAlert aria-hidden="true" />
      <AlertTitle>{t("missingRates.title")}</AlertTitle>
      <AlertDescription>
        <p>{t("missingRates.explanation")}</p>
        <ul className="list-disc pl-5">
          {missingRates.map((rate) => (
            <li key={`${rate.cost_category_id}-${rate.year.toString()}`}>
              {t("missingRates.rate", {
                category: rate.label ?? t("unnamed"),
                year: rate.year.toString(),
              })}
            </li>
          ))}
        </ul>
        {permissions.includes(`${rates.permission}.read`) ? (
          <Link
            href={rates.route}
            className="inline-flex items-center gap-1.5 font-medium text-foreground underline"
          >
            <Icon aria-hidden="true" className="size-3.5 shrink-0" />
            {permissions.includes(`${rates.permission}.write`)
              ? t("missingRates.enter")
              : t("missingRates.see")}
          </Link>
        ) : null}
      </AlertDescription>
    </Alert>
  );
}

/** A figure of the estimate: its name, and its amount. */
function Figure({ name, amount }: { readonly name: string; readonly amount: string }) {
  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-muted-foreground">{name}</dt>
      <dd className="font-semibold tabular-nums">{amount}</dd>
    </div>
  );
}

/** A breakdown of the total: each key named, its amount and, when given, its share. */
function Breakdown({
  name,
  items,
}: {
  readonly name: string;
  readonly items: readonly AmountByKey[];
}) {
  const t = useTranslations();
  const locale = useLocale();
  if (items.length === 0) {
    return null;
  }
  return (
    <div className="space-y-0.5">
      <dt className="text-xs text-muted-foreground">{name}</dt>
      <dd>
        <ul className="flex flex-wrap gap-x-4 gap-y-0.5">
          {items.map((item) => {
            const amount = formatMoney(item.amount, locale);
            const label =
              item.label ??
              (item.key === UNASSIGNED
                ? t("enums.Scope.unassigned")
                : t("estimateSummary.unnamed"));
            return (
              <li key={item.key} className="flex gap-1">
                <span>{label}</span>
                <span className="tabular-nums">
                  {item.share === undefined
                    ? amount
                    : t("estimateSummary.share", {
                        amount,
                        share: formatPercent(item.share, locale),
                      })}
                </span>
              </li>
            );
          })}
        </ul>
      </dd>
    </div>
  );
}

/** The figures of the indicators: the total, the provisions, the deviation, the breakdowns. */
function Figures({ indicators }: { readonly indicators: EstimateIndicators }) {
  const t = useTranslations("estimateSummary");
  const locale = useLocale();
  const delta = indicators.delta_to_previous_revision;
  const provisions = indicators.provisions_identified;
  return (
    <dl className="flex flex-wrap gap-x-8 gap-y-2">
      <Figure name={t("total")} amount={formatMoney(indicators.total, locale)} />
      {provisions === undefined ? null : (
        <Figure name={t("provisions")} amount={formatMoney(provisions, locale)} />
      )}
      {delta === null || delta === undefined ? null : (
        <Figure name={t("delta")} amount={formatMoney(delta, locale)} />
      )}
      <Breakdown name={t("byCostType")} items={indicators.by_cost_type} />
      <Breakdown name={t("bySubproject")} items={indicators.by_subproject} />
    </dl>
  );
}

/** Render what the screen of the estimate says above its grid. */
export function EstimateSummary({ indicators, missingRates, permissions }: EstimateSummaryProps) {
  const t = useTranslations("estimateSummary");
  const heading = useId();
  return (
    <div className="space-y-3">
      <MissingRatesNotice missingRates={missingRates} permissions={permissions} />
      <section aria-labelledby={heading} className="space-y-1.5 text-sm">
        <div className="flex flex-wrap items-baseline gap-x-3">
          <h2 id={heading} className="text-sm font-semibold">
            {t("title")}
          </h2>
          {indicators === undefined ? null : <CalculationDate context={indicators.context} />}
        </div>
        {indicators === undefined ? (
          <p className="text-muted-foreground">{t("unavailable")}</p>
        ) : (
          <Figures indicators={indicators} />
        )}
      </section>
    </div>
  );
}
