// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The report of the occurrence of a risk, shown in the confirmation of « Déclarer survenu »
 * (US-0680, US-3140, WF-RIS-0060, WF-IHM-0110): the report of the merge of what the own estimate
 * designates, in the order of what the occurrence does to the main structure — what it adds and
 * modifies, and the tasks it abandons, kept (`Differences`, in the marks `+`, `-`, `M` of the diff of
 * the grids); the tasks it completes and the earned value they bring at once; the completed tasks it
 * reopens and the earned value that falls back; the provision withdrawn from the remaining to commit;
 * the motives that refuse it, with which the declaration is not offered. A declaration asked while no
 * revision is in progress says it first creates one by copy (`creates_current_revision`). The two
 * signals of EP-08, an own estimate starting before the day of the declaration and the tasks a graft
 * redated, are gone with the graft (#4133, #4134).
 *
 * The front computes nothing of the report: the differences are in the order received, and the
 * amounts are the ones the server rendered.
 */
"use client";

import { useLocale, useMessages, useTranslations } from "next-intl";
import { useEffect } from "react";

import { readRiskOccurrenceReport } from "@/api/actions/risks";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { type ObjectNames, OutcomeNotice } from "@/components/commands/outcome-notice";
import { Differences } from "@/components/exchanges/import-report";
import { useCurrency } from "@/currency/context";
import { formatMoney } from "@/i18n/format";
import { problemMessage } from "@/i18n/problem";

/** The report of the occurrence of a risk, as the contract gives it. */
export type OccurrenceReport = components["schemas"]["RiskOccurrenceReport"];

const HEADING = "text-sm font-semibold";

/** The report as the server read it, and the motives that refuse it. */
export function ReportBody({ report }: { readonly report: OccurrenceReport }) {
  const t = useTranslations("riskOccurrenceReport");
  const locale = useLocale();
  const currency = useCurrency();
  const messages = useMessages();
  const { completed_tasks: completed = [], reopened_tasks: reopened = [] } = report;
  const money = (amount: string) => formatMoney(amount, locale, currency);
  return (
    <div className="space-y-3">
      {report.creates_current_revision ? <p role="note">{t("createsRevision")}</p> : null}
      <Differences differences={report.differences} marks />
      {completed.length === 0 && report.earned_value_added === undefined ? null : (
        <section aria-label={t("completedTitle")} className="space-y-1">
          <h3 className={HEADING}>{t("completed", { count: completed.length })}</h3>
          {completed.length === 0 ? null : (
            <ul className="list-inside list-disc">
              {completed.map((task) => (
                <li key={task.lineage_id}>{t("completedTask", { label: task.label })}</li>
              ))}
            </ul>
          )}
          {report.earned_value_added === undefined ? null : (
            <p className="tabular-nums">
              {t("earnedAdded", { amount: money(report.earned_value_added) })}
            </p>
          )}
        </section>
      )}
      {reopened.length === 0 && report.earned_value_removed === undefined ? null : (
        <section aria-label={t("reopenedTitle")} className="space-y-1">
          <h3 className={HEADING}>{t("reopened", { count: reopened.length })}</h3>
          {reopened.length === 0 ? null : (
            <ul className="list-inside list-disc">
              {reopened.map((task) => (
                <li key={task.lineage_id}>{t("reopenedTask", { label: task.label })}</li>
              ))}
            </ul>
          )}
          {report.earned_value_removed === undefined ? null : (
            <p className="tabular-nums">
              {t("earnedRemoved", { amount: money(report.earned_value_removed) })}
            </p>
          )}
        </section>
      )}
      <p>{t("provision", { amount: money(report.provision_amount) })}</p>
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
        </div>
      )}
    </div>
  );
}

/** What the confirmation shows of the report, read when it opens and read anew on demand. */
export function OccurrencePanel({
  projectId,
  riskId,
  subject,
  attempt,
  report,
  onRead,
  names,
}: {
  readonly projectId: string;
  readonly riskId: string;
  readonly subject: string;
  /** Bumped to read the report anew. */
  readonly attempt: number;
  readonly report: Outcome<OccurrenceReport> | undefined;
  readonly onRead: (report: Outcome<OccurrenceReport> | undefined) => void;
  readonly names: ObjectNames;
}) {
  const t = useTranslations("riskOccurrenceReport");
  useEffect(() => {
    let current = true;
    onRead(undefined);
    void readRiskOccurrenceReport(projectId, riskId).then((read) => {
      if (current) {
        onRead(read);
      }
    });
    return () => {
      current = false;
    };
  }, [projectId, riskId, attempt, onRead]);
  return (
    <section aria-label={t("title")} aria-busy={report === undefined} className="space-y-2">
      <h2 className={HEADING}>{t("title")}</h2>
      {report === undefined ? <p role="status">{t("reading")}</p> : null}
      {report?.kind === "done" ? <ReportBody report={report.data} /> : null}
      {report !== undefined && report.kind !== "done" ? (
        <OutcomeNotice
          outcome={report}
          names={names}
          subject={subject}
          onClear={() => {
            onRead(undefined);
          }}
        />
      ) : null}
    </section>
  );
}
