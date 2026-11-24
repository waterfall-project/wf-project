// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The update of an amendment in arrears (US-2640, US-3050, #4034), from the grid of its differential:
 * the main structure has received writes since the base of the differential, and the merge is not
 * offered before the differential carries them. The command opens a confirmation in the page, which
 * first reads the report of the update (`getStructureRebaseReport`) and presents it — what the main
 * structure received and the update carries into the differential, `added`, `updated`, `removed`;
 * what the differential keeps, `kept`, with the fields it keeps; the motives that refuse it, with
 * which the update cannot be confirmed —, then confirms with the two counters the report read
 * (`rebaseCostStructure`); the page is read anew, the grid with it. A report gone stale (412) offers
 * to read it anew. Abandoning sends nothing: the report is a read.
 *
 * The front computes nothing of the report: the differences are in the order received, the counts are
 * the lengths of what the server rendered.
 */
"use client";

import { useLocale, useMessages, useTranslations } from "next-intl";
import { useCallback, useEffect, useState } from "react";

import { readRebaseReport, rebaseAmendment } from "@/api/actions/revisions";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { ConfirmedCommand } from "@/components/commands/confirmed-command";
import { commandIcon, STRUCTURE_COMMAND_ICONS } from "@/components/commands/icons";
import type { CommandOffer } from "@/components/commands/offer";
import { type ObjectNames, OutcomeNotice } from "@/components/commands/outcome-notice";
import { Differences } from "@/components/exchanges/report-tables";
import { problemMessage } from "@/i18n/problem";

type Report = components["schemas"]["StructureRebaseReport"];

/** The amendment an update is about, and where it is. */
export interface RebasedAmendment {
  readonly projectId: string;
  readonly revisionId: string;
  readonly structureId: string;
  readonly label: string;
}

const HEADING = "text-sm font-semibold";
const CHANGES = ["added", "updated", "removed", "kept"] as const;

/** The report as the server read it: the counts of what it carries and keeps, the motives, the differences. */
function ReportBody({ report }: { readonly report: Report }) {
  const t = useTranslations("rebaseReport");
  const locale = useLocale();
  const messages = useMessages();
  return (
    <div className="space-y-3">
      <ul aria-label={t("counts")} className="space-y-0.5">
        {CHANGES.map((change) => (
          <li key={change} className="tabular-nums">
            {t(change, { count: report.differences.filter((one) => one.change === change).length })}
          </li>
        ))}
      </ul>
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
      <Differences differences={report.differences} marks />
    </div>
  );
}

/** What the form shows of the report, read when it opens and read anew on demand. */
function ReportPanel({
  amendment,
  attempt,
  report,
  onRead,
  names,
}: {
  readonly amendment: RebasedAmendment;
  readonly attempt: number;
  readonly report: Outcome<Report> | undefined;
  readonly onRead: (report: Outcome<Report> | undefined) => void;
  readonly names: ObjectNames;
}) {
  const t = useTranslations("rebaseReport");
  const { projectId, revisionId, structureId } = amendment;
  useEffect(() => {
    let current = true;
    onRead(undefined);
    void readRebaseReport(projectId, revisionId, structureId).then((read) => {
      if (current) {
        onRead(read);
      }
    });
    return () => {
      current = false;
    };
  }, [projectId, revisionId, structureId, attempt, onRead]);
  return (
    <section aria-label={t("title")} aria-busy={report === undefined} className="space-y-2">
      <h2 className={HEADING}>{t("title")}</h2>
      {report === undefined ? <p role="status">{t("reading")}</p> : null}
      {report?.kind === "done" ? <ReportBody report={report.data} /> : null}
      {report !== undefined && report.kind !== "done" ? (
        <OutcomeNotice
          outcome={report}
          names={names}
          subject={amendment.label}
          onClear={() => {
            onRead(undefined);
          }}
        />
      ) : null}
    </section>
  );
}

/** Offer the update of the amendment a grid reads, when its structure lists `rebase` available. */
export function RebaseAmendmentCommand({
  offer,
  amendment,
  names,
}: {
  readonly offer: CommandOffer;
  readonly amendment: RebasedAmendment;
  readonly names: ObjectNames;
}) {
  const t = useTranslations("rebaseReport");
  const helps = useTranslations("commands");
  const [report, setReport] = useState<Outcome<Report>>();
  const [attempt, setAttempt] = useState(0);
  const read = report?.kind === "done" ? report.data : undefined;
  const onRead = useCallback((next: Outcome<Report> | undefined) => {
    setReport(next);
  }, []);
  const { projectId, revisionId, structureId } = amendment;
  const run = () =>
    read === undefined
      ? Promise.reject(new Error("the update is confirmed once its report is read"))
      : rebaseAmendment(projectId, revisionId, structureId, {
          mainStructureLockVersion: read.main_structure_lock_version,
          structureLockVersion: read.structure_lock_version,
        });
  return (
    <ConfirmedCommand
      offer={offer}
      label={t("label")}
      help={helps("structure.rebase.help")}
      icon={commandIcon(STRUCTURE_COMMAND_ICONS.rebase)}
      statement={t("statement")}
      submit={t("submit")}
      ready={read?.refusals.length === 0}
      names={names}
      subject={amendment.label}
      run={run}
      done={() => t("done", { label: amendment.label })}
      reread={{
        label: t("reread"),
        run: () => {
          setAttempt(attempt + 1);
        },
      }}
    >
      <ReportPanel
        amendment={amendment}
        attempt={attempt}
        report={report}
        onRead={onRead}
        names={names}
      />
    </ConfirmedCommand>
  );
}
