// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The report of an import, as `getImport` gives it (WF-INTF-0080): the file, its kind and where the
 * import stands, when it was opened and until when its report applies; then, once analysed, the
 * lines read, of which those left as they are, the reasons that ask for an explicit confirmation,
 * each line rejected by its place in the file — its tab, when the file has tabs, and its row — and
 * its motive, each task the file dates or lasts otherwise than Waterfall computes it, with the
 * columns that differ (WF-INTF-0040), each value of the file kept and signalled, each task the
 * import completes at the date of the review the file bears, the unit constants of an MS Project
 * file that differ from the installation's, with both (WF-PLA-0160), and each difference with the
 * existing data — a line of actual cost by its document and its item (US-0630) —, with the fields
 * it changes named as the columns of their grid, and what the import ignores — the columns of an
 * extraction of actual costs by the label the file gives them (WF-REF-0190). Every sentence is the
 * catalogue's, written from the codes the API gives (WF-ARC-0110): a motive from its code and
 * parameters, as a refusal is; the label of a line, which comes from the file or the project, as it
 * is. The front counts, sorts and filters nothing: the lists are in the order received. Under it,
 * its application and its abandonment (`ReportCommands`).
 */
import { FileSpreadsheet } from "lucide-react";
import { useFormatter, useLocale, useMessages, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { findOffer } from "@/components/commands/offer";
import { LocalTime } from "@/components/local-time";
import { CELL, ListTable } from "@/components/projects/project-tables";
import { SectionCard } from "@/components/shell/section-card";
import { TableCell, TableRow } from "@/components/ui/table";
import { formatDecimal, formatPlanningDate } from "@/i18n/format";
import { problemMessage } from "@/i18n/problem";

import { CalendarGap } from "./calendar-gap";
import { DurationRule } from "./duration-rule";
import { ReportCommands } from "./report-commands";
import { Differences, Rejections } from "./report-tables";

type Import = components["schemas"]["ImportDetail"];
type Report = components["schemas"]["ImportReport"];

const HEADING = "text-sm font-semibold";
const MUTED = "text-sm text-muted-foreground";

/**
 * The reasons that reject the whole file (`refusals`, WF-INTF-0040, WF-PLA-0150, WF-PLA-0170), each
 * by its sentence, the tasks it names by their labels, in the order received: nothing is applied,
 * not even the lines accepted.
 */
function Refusals({ refusals }: { readonly refusals: Report["refusals"] }) {
  const t = useTranslations("exchanges.report");
  const locale = useLocale();
  const messages = useMessages();
  return (
    <div role="alert" className="space-y-1 text-destructive">
      <h3 className={HEADING}>{t("refusals", { count: refusals.length })}</h3>
      <ul className="list-inside list-disc text-sm">
        {refusals.map((refusal, index) => (
          <li key={`${refusal.code}-${String(index)}`}>
            {problemMessage(refusal, { locale, messages })}
          </li>
        ))}
      </ul>
    </div>
  );
}

/**
 * The WBS elements of an extraction of actual costs that are neither the code of the project nor
 * that of one of its subprojects, each as the file carries it and the number of its lines, in the
 * order received (`unknown_wbs_elements`, WF-CRE-0020): the user declares the subprojects the
 * file means, then imports again. A line without an element is named as such. The front counts
 * nothing: the number of lines is the API's.
 */
function UnknownElements({ elements }: { readonly elements: Report["unknown_wbs_elements"] }) {
  const t = useTranslations("exchanges.report");
  const locale = useLocale();
  return (
    <div className="space-y-1">
      <h3 className={HEADING}>{t("unknownElements", { count: elements.length })}</h3>
      <ListTable label={t("unknownElementsTable")} columns={[t("wbsElement"), t("lineCount")]}>
        {elements.map(({ wbs_element: element, line_count: count }, index) => (
          <TableRow key={`${element}-${String(index)}`}>
            <TableCell className={CELL}>{element === "" ? t("withoutElement") : element}</TableCell>
            <TableCell className={`${CELL} tabular-nums`}>
              {formatDecimal(String(count), locale)}
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </div>
  );
}

/**
 * What the import ignores, each kind by its name, its count and the names of what it ignores when
 * the file gives them — for the columns of an extraction of actual costs, the labels as the file
 * carries them (WF-REF-0190), left as they are.
 */
function Ignored({ ignored }: { readonly ignored: Report["ignored"] }) {
  const t = useTranslations();
  const format = useFormatter();
  return (
    <div className="space-y-1">
      <h3 className={HEADING}>{t("exchanges.report.ignored")}</h3>
      <ul className="list-inside list-disc text-sm">
        {ignored.map(({ kind, count, labels }) => {
          const name = t(`enums.ImportIgnoredKind.${kind}`);
          return (
            <li key={kind}>
              {labels.length === 0
                ? t("exchanges.report.ignoredCount", { kind: name, count })
                : t("exchanges.report.ignoredItem", {
                    kind: name,
                    count,
                    names: format.list(labels, { type: "conjunction" }),
                  })}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/**
 * What the import keeps as the file bears it and signals, or corrects: each task by its label, the
 * column that bears the value, the kind of signal and its sentence, from the code and the
 * parameters the API gives, as a refusal of an entry is (WF-INTF-0040, WF-PLA-0020), in the order
 * received.
 */
function Signals({ signals }: { readonly signals: Report["signals"] }) {
  const t = useTranslations();
  const locale = useLocale();
  const messages = useMessages();
  return (
    <div className="space-y-1">
      <h3 className={HEADING}>{t("exchanges.report.signals", { count: signals.length })}</h3>
      <ListTable
        label={t("exchanges.report.signalsTable")}
        columns={[
          t("exchanges.report.task"),
          t("exchanges.report.column"),
          t("exchanges.report.signal"),
          t("exchanges.report.motive"),
        ]}
      >
        {signals.map((signal, index) => (
          <TableRow key={`${signal.lineage_id ?? "new"}-${signal.code}-${String(index)}`}>
            <TableCell className={CELL}>{signal.label}</TableCell>
            <TableCell className={CELL}>{t(`enums.NodeColumn.${signal.column}`)}</TableCell>
            <TableCell className={CELL}>{t(`enums.ImportSignal.code.${signal.code}`)}</TableCell>
            <TableCell className={CELL}>{problemMessage(signal, { locale, messages })}</TableCell>
          </TableRow>
        ))}
      </ListTable>
    </div>
  );
}

/**
 * The tasks the file dates or lasts otherwise than Waterfall computes them from their durations,
 * their links and their calendars, each by its label and the columns that differ, named as the
 * columns of the planning (WF-INTF-0040), in the order received: what Waterfall computes prevails,
 * and nothing is to confirm.
 */
function DateMismatches({ mismatches }: { readonly mismatches: Report["date_mismatches"] }) {
  const t = useTranslations();
  const format = useFormatter();
  return (
    <div className="space-y-1">
      <h3 className={HEADING}>
        {t("exchanges.report.dateMismatches", { count: mismatches.length })}
      </h3>
      <ListTable
        label={t("exchanges.report.dateMismatchesTable")}
        columns={[t("exchanges.report.task"), t("exchanges.report.fields")]}
      >
        {mismatches.map((task, index) => (
          <TableRow key={`${task.lineage_id ?? "new"}-${String(index)}`}>
            <TableCell className={CELL}>{task.label}</TableCell>
            <TableCell className={CELL}>
              {format.list(
                task.fields.map((field) => t(`enums.NodeColumn.${field}`)),
                { type: "conjunction" },
              )}
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </div>
  );
}

/**
 * The tasks the import completes, each with the date it takes: the date of the review the file
 * bears, which the analysis read (WF-INTF-0120, WF-INTF-0130), in the order received. An import
 * never leaves the date null (the contract); only a merge does, and it shows no date.
 */
function CompletedTasks({ completed }: { readonly completed: Report["completed_tasks"] }) {
  const t = useTranslations("exchanges.report");
  const locale = useLocale();
  return (
    <div className="space-y-1">
      <h3 className={HEADING}>{t("completed", { count: completed.length })}</h3>
      <ListTable label={t("completedTable")} columns={[t("task"), t("completedOn")]}>
        {completed.map((task) => (
          <TableRow key={task.lineage_id}>
            <TableCell className={CELL}>{task.label}</TableCell>
            <TableCell className={CELL}>
              {task.completed_on === null ? null : formatPlanningDate(task.completed_on, locale)}
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </div>
  );
}

/**
 * The unit constants of an MS Project schedule that differ from those of the installation, the
 * file's and the installation's, as the API gives them (WF-PLA-0160): the durations and the lags
 * keep their hours. A piece of information, not a reason to confirm.
 */
function UnitConstants({
  constants,
}: {
  readonly constants: NonNullable<Report["unit_constants"]>;
}) {
  const t = useTranslations("exchanges.report");
  const locale = useLocale();
  const { file, installation } = constants;
  return (
    <p className="text-sm">
      {t("unitConstants", {
        fileDay: formatDecimal(file.hours_per_day, locale),
        fileWeek: formatDecimal(file.hours_per_week, locale),
        fileMonth: formatDecimal(file.days_per_month, locale),
        installationDay: formatDecimal(installation.hours_per_day, locale),
        installationWeek: formatDecimal(installation.hours_per_week, locale),
        installationMonth: formatDecimal(installation.days_per_month, locale),
      })}
    </p>
  );
}

/**
 * What the analysis found: lines read, the unit constants of the file, reasons to confirm, lines
 * rejected, differences.
 */
function Findings({ report }: { readonly report: Report }) {
  const t = useTranslations();
  const reasons = report.requires_confirmation_reasons;
  return (
    <div className="space-y-3">
      <p className="text-sm">
        {t("exchanges.report.read", { count: report.read_count })}{" "}
        {t("exchanges.report.unchanged", { count: report.unchanged_count })}
      </p>
      {report.unit_constants === null ? null : <UnitConstants constants={report.unit_constants} />}
      {report.calendar_gap === null ? null : <CalendarGap gap={report.calendar_gap} />}
      {reasons.length === 0 ? null : (
        <div className="space-y-1">
          <h3 className={HEADING}>{t("exchanges.report.reasons")}</h3>
          <ul className="list-inside list-disc text-sm">
            {reasons.map((reason) => (
              <li key={reason}>
                {t(`enums.ImportReport.requires_confirmation_reasons.${reason}`)}
              </li>
            ))}
          </ul>
        </div>
      )}
      {report.refusals.length === 0 ? null : <Refusals refusals={report.refusals} />}
      <Rejections rejected={report.rejected} />
      {report.unknown_wbs_elements.length === 0 ? null : (
        <UnknownElements elements={report.unknown_wbs_elements} />
      )}
      <Differences differences={report.differences} limited />
      {report.date_mismatches.length === 0 ? null : (
        <DateMismatches mismatches={report.date_mismatches} />
      )}
      {report.signals.length === 0 ? null : <Signals signals={report.signals} />}
      {report.completed_tasks.length === 0 ? null : (
        <CompletedTasks completed={report.completed_tasks} />
      )}
      {report.ignored.length === 0 ? null : <Ignored ignored={report.ignored} />}
    </div>
  );
}

/** The import a report is of, which lists its own commands, and where the screen started. */
export interface ImportReportProps {
  readonly projectId: string;
  readonly entry: Import;
  readonly start: string;
  /** Where the screen leads once the import is applied — the planning it fills, if it is one. */
  readonly then?: string | undefined;
}

/** Render the report of an import, and offer to apply or abandon it. */
export function ImportReport({ projectId, entry, start, then }: ImportReportProps) {
  const t = useTranslations();
  const title = t("exchanges.report.title", { file: entry.filename });
  return (
    <SectionCard title={title} icon={FileSpreadsheet}>
      <div className="flex min-w-0 flex-col gap-3">
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-sm">
          <dt className="text-muted-foreground">{t("exchanges.report.kind")}</dt>
          <dd>{t(`enums.ExchangeKind.${entry.kind}`)}</dd>
          <dt className="text-muted-foreground">{t("exchanges.report.status")}</dt>
          <dd>{t(`enums.Import.status.${entry.status}`)}</dd>
          <dt className="text-muted-foreground">{t("exchanges.report.openedAt")}</dt>
          <dd>
            <LocalTime value={entry.created_at} />
          </dd>
          {entry.expires_at === null ? null : (
            <>
              <dt className="text-muted-foreground">{t("exchanges.report.expiresAt")}</dt>
              <dd>
                <LocalTime value={entry.expires_at} />
              </dd>
            </>
          )}
          {entry.report?.format_version == null ? null : (
            <>
              <dt className="text-muted-foreground">{t("exchanges.report.formatVersion")}</dt>
              <dd>{entry.report.format_version}</dd>
            </>
          )}
        </dl>
        {entry.status === "refused" ? (
          <p role="note" className={MUTED}>
            {t("exchanges.refused")}
          </p>
        ) : null}
        {entry.report == null ? (
          <p className={MUTED}>
            {t(
              entry.status === "analysing"
                ? "exchanges.report.analysing"
                : entry.status === "failed"
                  ? "exchanges.report.failed"
                  : "exchanges.report.none",
            )}
          </p>
        ) : (
          <Findings report={entry.report} />
        )}
        <DurationRule
          key={`rule-${entry.import_id}`}
          projectId={projectId}
          importId={entry.import_id}
          filename={entry.filename}
          rule={entry.report?.calendar_gap?.duration_rule}
          awaiting={entry.status === "analysed"}
          task={entry.status === "analysing" ? entry.task?.task_id : undefined}
        />
        {/* Its own commands, as the import lists them: an outcome or an open
          confirmation stays with its import. */}
        <ReportCommands
          key={entry.import_id}
          projectId={projectId}
          importId={entry.import_id}
          filename={entry.filename}
          apply={findOffer(entry.available_commands, "apply")}
          abandon={findOffer(entry.available_commands, "abandon")}
          start={start}
          then={then}
        />
      </div>
    </SectionCard>
  );
}
