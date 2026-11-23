// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The report of the update of a structure, as the server read it (US-2640, US-3140): the counts of
 * what the update carries and keeps, the motives that refuse it, the differences in the order
 * received, and — for the own estimate of a risk — the severity and the provision it would record.
 * Shared by the command that updates an amendment or an own estimate (`rebase-structure-command.tsx`)
 * and by the prompt of an own estimate updated before an entry (`own-estimate-entry.tsx`).
 *
 * The front computes nothing of it: the counts are the lengths of what the server rendered.
 */
"use client";

import { useLocale, useMessages, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { Differences } from "@/components/exchanges/import-report";
import { useCurrency } from "@/currency/context";
import { formatMoney } from "@/i18n/format";
import { problemMessage } from "@/i18n/problem";

/** The report of the update of a structure. */
export type Report = components["schemas"]["StructureRebaseReport"];

/** What a report is about: an amendment, or the own estimate of a risk. */
export type RebaseNature = "amendment" | "risk";

const HEADING = "text-sm font-semibold";
const CHANGES = ["added", "updated", "removed", "kept"] as const;

/**
 * Whether the report signals something: a value the structure keeps against the project, or a motive
 * that refuses the update. A report that signals nothing is applied without a question (WF-RIS-0070);
 * the severity it recomputes is not a signal.
 */
export function signals(report: Report): boolean {
  return report.refusals.length > 0 || report.differences.some((one) => one.change === "kept");
}

/** The report as the server read it. */
export function ReportBody({
  report,
  nature,
}: {
  readonly report: Report;
  readonly nature: RebaseNature;
}) {
  const t = useTranslations("rebaseReport");
  const locale = useLocale();
  const messages = useMessages();
  const currency = useCurrency();
  const { severity, provision_amount: provision } = report;
  return (
    <div className="space-y-3">
      <ul aria-label={t("counts")} className="space-y-0.5">
        {CHANGES.map((change) => (
          <li key={change} className="tabular-nums">
            {t(nature === "risk" && change === "kept" ? "keptOwn" : change, {
              count: report.differences.filter((one) => one.change === change).length,
            })}
          </li>
        ))}
      </ul>
      {nature === "risk" && severity != null && provision != null ? (
        <ul aria-label={t("recomputed")} className="space-y-0.5 tabular-nums">
          <li>{t("severity", { amount: formatMoney(severity, locale, currency) })}</li>
          <li>{t("provision", { amount: formatMoney(provision, locale, currency) })}</li>
        </ul>
      ) : null}
      {report.refusals.length === 0 ? null : (
        <div role="alert" className="space-y-1 text-destructive">
          <h3 className={HEADING}>{t("refusals", { count: report.refusals.length })}</h3>
          <ul className="list-inside list-disc">
            {report.refusals.map((refusal, index) => (
              <li key={`${refusal.code}-${String(index)}`}>
                {problemMessage(refusal, { locale, messages })}
              </li>
            ))}
          </ul>
          {nature === "risk" ? <p>{t("correctOwn")}</p> : null}
        </div>
      )}
      <Differences differences={report.differences} marks />
    </div>
  );
}
