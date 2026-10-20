// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the screen of the estimate says above its grid: the hourly rates missing for its
 * calculation (WF-DEV-0010), each category named with its year, and the way to the reference
 * where rates are entered when the session may read it; then the indicators of the estimate
 * (WF-DEV-0060) — its total, its provisions, its deviations from the reference and from the
 * previous marked revision, its totals by nature of cost, in amount and in share of the total, by
 * sub-project and by work package (#220) —, with the date they are computed at (WF-IHM-0020), or
 * that they are unavailable when the API did not give them.
 *
 * The figures lie in cards (`FiguresCard`, US-0550): the total with its deviations, then one card for each breakdown.
 *
 * Every figure is the API's, formatted in the language of the interface from its exact string:
 * nothing is summed, nor divided, nor hidden by a rule of the front (WF-ARC-0020). A deviation
 * the API does not give is not shown as zero: it is left out, as are the totals by work package of a
 * planning that is not structured in work packages — absent rather than nil. An amount the API
 * cannot compute — an hourly rate missing (WF-DEV-0010) — is said so, with its reason, never made
 * up. A name the API leaves out is said missing, never replaced by an identifier.
 */
import { TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";

import { FUNCTION_ICONS } from "@/components/shell/function-display";

import type { components, operations } from "@/api/generated/schema";
import { platformOffer } from "@/components/commands/offer";
import { FigureTerm, FiguresCard, FiguresGrid, FiguresList } from "@/components/figures-card";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { formatMoney, formatShare } from "@/i18n/format";
import { functionOf } from "@/navigation/functions";

/** The indicators of an estimate, as the API computes them. */
export type EstimateIndicators = components["schemas"]["EstimateIndicators"];

/** The categories and years whose hourly rate the calculation of an estimate lacks. */
export type MissingRates =
  operations["getMissingRates"]["responses"][200]["content"]["application/json"];

/** A permission of the catalogue (WF-ADM-0100). */
type Permission = components["schemas"]["PermissionCode"];

/** An amount by key — a nature of cost, a sub-project, a work package —, maybe not computable. */
type AmountByKey = components["schemas"]["ComputableAmountByKey"];

/** A value that may not be computable (WF-IND-0010). */
type Computable = components["schemas"]["Computable"];

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
            {platformOffer(permissions, "cost_settings") !== undefined
              ? t("missingRates.enter")
              : t("missingRates.see")}
          </Link>
        ) : null}
      </AlertDescription>
    </Alert>
  );
}

/**
 * A value the API may not have computed, written by `format` when it has — or said not
 * computable, with the reason the API codes, in the sentence of the catalogue.
 */
function Figured({
  value,
  format,
}: {
  readonly value: Computable;
  readonly format: (value: string) => string;
}) {
  const t = useTranslations();
  // A value the API calls computable yet leaves out is not made up either: it is said missing.
  const computed = value.is_computable ? (value.value ?? null) : null;
  if (computed !== null) {
    return format(computed);
  }
  const reason = value.reason ?? null;
  return reason === null
    ? t("indicator.notComputable")
    : t("estimateSummary.notComputable", { reason: t(`enums.NotComputableReason.${reason}`) });
}

/**
 * A figure of the estimate: its name, and its amount — one the API always computes, as a
 * `Money`, or one it may not have, under `Computable`.
 */
function Figure({ name, amount }: { readonly name: string; readonly amount: Computable | string }) {
  const locale = useLocale();
  return (
    <FigureTerm name={name}>
      {typeof amount === "string" ? (
        formatMoney(amount, locale)
      ) : (
        <Figured value={amount} format={(value) => formatMoney(value, locale)} />
      )}
    </FigureTerm>
  );
}

/** A breakdown of the total, in a card of its own: each key named, its amount and, when given, its share. */
function Breakdown({
  name,
  items,
  context,
}: {
  readonly name: string;
  readonly items: readonly AmountByKey[];
  readonly context: EstimateIndicators["context"];
}) {
  const t = useTranslations();
  const bounds = useTranslations("share");
  const locale = useLocale();
  if (items.length === 0) {
    return null;
  }
  return (
    <FiguresCard title={name} context={context}>
      <ul className="space-y-1 text-xs leading-snug">
        {items.map((item) => {
          const label =
            item.label ??
            (item.key === UNASSIGNED ? t("enums.Scope.unassigned") : t("estimateSummary.unnamed"));
          const share = item.share;
          return (
            <li key={item.key} className="flex flex-wrap gap-x-1">
              <span>{label}</span>
              <span className="tabular-nums">
                <Figured value={item.amount} format={(value) => formatMoney(value, locale)} />
                {share?.is_computable === true && share.value !== null && share.value !== undefined
                  ? t("estimateSummary.shareOf", {
                      share: formatShare(share.value, locale, bounds),
                    })
                  : null}
              </span>
            </li>
          );
        })}
      </ul>
    </FiguresCard>
  );
}

/** The cards of the indicators: the total, the provisions and the deviations, then the breakdowns. */
function Figures({ indicators }: { readonly indicators: EstimateIndicators }) {
  const t = useTranslations("estimateSummary");
  const reference = indicators.delta_to_reference;
  const delta = indicators.delta_to_previous_revision;
  const provisions = indicators.provisions_identified;
  const { context } = indicators;
  return (
    <FiguresGrid>
      <FiguresCard title={t("title")} context={context}>
        <FiguresList>
          <Figure name={t("total")} amount={indicators.total} />
          {provisions === undefined ? null : <Figure name={t("provisions")} amount={provisions} />}
          {reference === null ? null : <Figure name={t("deltaToReference")} amount={reference} />}
          {delta === null || delta === undefined ? null : (
            <Figure name={t("delta")} amount={delta} />
          )}
        </FiguresList>
      </FiguresCard>
      <Breakdown name={t("byCostType")} items={indicators.by_cost_type} context={context} />
      <Breakdown name={t("bySubproject")} items={indicators.by_subproject} context={context} />
      <Breakdown name={t("byWorkPackage")} items={indicators.by_work_package} context={context} />
    </FiguresGrid>
  );
}

/** Render what the screen of the estimate says above its grid. */
export function EstimateSummary({ indicators, missingRates, permissions }: EstimateSummaryProps) {
  const t = useTranslations("estimateSummary");
  return (
    <div className="space-y-3">
      <MissingRatesNotice missingRates={missingRates} permissions={permissions} />
      {indicators === undefined ? (
        <FiguresGrid>
          <FiguresCard title={t("title")}>
            <p className="text-muted-foreground">{t("unavailable")}</p>
          </FiguresCard>
        </FiguresGrid>
      ) : (
        <Figures indicators={indicators} />
      )}
    </div>
  );
}
