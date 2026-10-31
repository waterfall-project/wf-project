// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The report of an import, as `getImport` gives it (WF-INTF-0080): the file, its kind and where
 * the import stands, when it was opened and until when its report applies; then, once analysed,
 * the lines read, of which those left as they are, the reasons that ask for an explicit
 * confirmation, each line rejected by its place in the file and its motive, each value of the file
 * kept and signalled, each task the import completes at the date of the review the file bears, and
 * each difference with the existing data — a line of
 * actual cost by its document and its item (US-0630) —, with the fields it changes named as the
 * columns of their grid, and what the import ignores — the columns of an
 * extraction of actual costs by the label the file gives them (WF-REF-0190). Every sentence
 * is the catalogue's, written from the codes the API gives (WF-ARC-0110): a motive from its code
 * and parameters, as a refusal is; the label of a line, which comes from the file or the project,
 * as it is. The front counts, sorts and filters nothing: the lists are in the order received.
 * Under it, its application and its abandonment (`ReportCommands`).
 */
import { FileSpreadsheet } from "lucide-react";
import { useFormatter, useLocale, useMessages, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import type { CommandOffer } from "@/components/commands/offer";
import { LocalTime } from "@/components/local-time";
import { DiffMark } from "@/components/grid/diff-mark";
import type { RowDifference } from "@/components/grid/columns";
import { NODE_COLUMNS, type NodeColumn } from "@/components/grid/nodes";
import { CELL, ICON, ListTable } from "@/components/projects/project-tables";
import { TableCell, TableRow } from "@/components/ui/table";
import type { Catalogue } from "@/i18n/catalogues";
import { formatDecimal, formatPlanningDate } from "@/i18n/format";
import { problemMessage } from "@/i18n/problem";

import { IMPORT_STEPS } from "./offers";
import { ReportCommands } from "./report-commands";

type Import = components["schemas"]["Import"];
type Report = components["schemas"]["ImportReport"];
type Difference = Report["differences"][number];
type DifferenceField = NonNullable<Difference["fields"]>[number];

/**
 * The columns of a line of actual cost, every one of them, which its own catalogue names. The
 * generated type of `ActualCostColumn` is a mere string, the contract admitting the columns the
 * file kept (`passthrough.<column>`): the named ones are held by the catalogue instead, whose keys
 * `make catalogs` holds to the values the contract codes — one added fails the type check here.
 */
const ACTUAL_COST_COLUMNS = {
  document_date: true,
  document_number: true,
  document_item: true,
  amount: true,
  subproject: true,
} as const satisfies Record<keyof Catalogue["enums"]["ActualCostColumn"], true>;

/** A column of a line of actual cost that the catalogue names. */
type ActualCostColumn = keyof typeof ACTUAL_COST_COLUMNS;

/**
 * A column the file kept, `passthrough.<column>` (WF-CRE-0010, #365): named as the file names
 * it, which no catalogue translates.
 */
const PASSTHROUGH = "passthrough.";

/** Whether a field of a difference is a column of a line of actual cost. */
function isActualCostColumn(field: DifferenceField): field is ActualCostColumn {
  return Object.hasOwn(ACTUAL_COST_COLUMNS, field);
}

/** Whether a field of a difference is a column of the structure, which its catalogue names. */
function isNodeColumn(field: DifferenceField): field is NodeColumn {
  return (NODE_COLUMNS as readonly string[]).includes(field);
}

/** The mark of a grid each change of a report bears; a task kept bears none. */
const MARKED: Readonly<Record<Difference["change"], RowDifference | undefined>> = {
  added: "added",
  removed: "removed",
  updated: "modified",
  kept: undefined,
};

const HEADING = "text-sm font-semibold";
const MUTED = "text-sm text-muted-foreground";

/** The lines of the file rejected, each by its row and its motive, in the order received. */
function Rejections({ rejected }: { readonly rejected: Report["rejected"] }) {
  const t = useTranslations("exchanges.report");
  const locale = useLocale();
  const messages = useMessages();
  return (
    <div className="space-y-1">
      <h3 className={HEADING}>{t("rejected", { count: rejected.length })}</h3>
      {rejected.length === 0 ? null : (
        <ListTable label={t("rejectedTable")} columns={[t("row"), t("motive")]}>
          {rejected.map((line, index) => (
            <TableRow key={`${String(line.row)}-${String(index)}`}>
              <TableCell className={`${CELL} tabular-nums`}>
                {formatDecimal(String(line.row), locale)}
              </TableCell>
              <TableCell className={CELL}>{problemMessage(line, { locale, messages })}</TableCell>
            </TableRow>
          ))}
        </ListTable>
      )}
    </div>
  );
}

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
 * The differences with the existing data, each by its change, its object, its label and the fields
 * it changes, named by the catalogue of their columns (WF-ARC-0110), in the order received.
 */
export function Differences({
  differences,
  marks = false,
}: {
  readonly differences: Report["differences"];
  /** Whether each change bears the mark of the diff of a grid, `+`, `-`, `M` (US-0510). */
  readonly marks?: boolean;
}) {
  const t = useTranslations();
  const format = useFormatter();
  // A field is named by the catalogue of the columns of its object: a line of actual cost by its
  // own, a task, a line of the estimate or a link by the columns of the structure — `subproject`
  // is a column of both; the parent of a node, which no column holds, by its own key (#1194). A
  // field the object does not have is left unnamed, never guessed.
  const fieldName = (target: Difference["target"], field: DifferenceField) => {
    if (target === "actual_cost_line") {
      if (field.startsWith(PASSTHROUGH)) {
        return field.slice(PASSTHROUGH.length);
      }
      return isActualCostColumn(field) ? t(`enums.ActualCostColumn.${field}`) : undefined;
    }
    if (field === "subproject") {
      return t("enums.NodeColumn.subproject");
    }
    if (field === "parent" || field === "planning_start_on") {
      return t(`enums.ImportDifferenceField.${field}`);
    }
    return isNodeColumn(field) ? t(`enums.NodeColumn.${field}`) : undefined;
  };
  const fieldsOf = (difference: Difference) =>
    (difference.fields ?? []).flatMap((field) => fieldName(difference.target, field) ?? []);
  return (
    <div className="space-y-1">
      <h3 className={HEADING}>
        {t("exchanges.report.differences", { count: differences.length })}
      </h3>
      {differences.length === 0 ? null : (
        <ListTable
          label={t("exchanges.report.differencesTable")}
          columns={[
            t("exchanges.report.change"),
            t("exchanges.report.target"),
            t("exchanges.report.label"),
            t("exchanges.report.fields"),
          ]}
        >
          {differences.map((difference, index) => (
            <TableRow key={`${difference.lineage_id ?? "new"}-${String(index)}`}>
              <TableCell className={CELL}>
                {marks ? (
                  <span className="inline-flex gap-1.5">
                    <DiffMark difference={MARKED[difference.change]} />
                    <span aria-hidden="true">
                      {t(`enums.ImportDifference.change.${difference.change}`)}
                    </span>
                  </span>
                ) : (
                  t(`enums.ImportDifference.change.${difference.change}`)
                )}
              </TableCell>
              <TableCell className={CELL}>
                {t(`enums.ImportDifference.target.${difference.target}`)}
              </TableCell>
              <TableCell className={CELL}>
                {difference.label == null
                  ? t("exchanges.report.unnamed")
                  : difference.document_item == null
                    ? difference.label
                    : t("exchanges.report.labelItem", {
                        label: difference.label,
                        item: difference.document_item,
                      })}
              </TableCell>
              <TableCell className={CELL}>
                {format.list(fieldsOf(difference), { type: "conjunction" })}
              </TableCell>
            </TableRow>
          ))}
        </ListTable>
      )}
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
 * column that bears the value, the kind of signal and its sentence, from the code and the parameters
 * the API gives, as a refusal of an entry is (WF-INTF-0040, WF-PLA-0020), in the order received.
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

/** What the analysis found: lines read, reasons to confirm, lines rejected, differences. */
function Findings({ report }: { readonly report: Report }) {
  const t = useTranslations();
  const reasons = report.requires_confirmation_reasons;
  return (
    <div className="space-y-3">
      <p className="text-sm">
        {t("exchanges.report.read", { count: report.read_count })}{" "}
        {t("exchanges.report.unchanged", { count: report.unchanged_count })}
      </p>
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
      <Differences differences={report.differences} />
      {report.signals.length === 0 ? null : <Signals signals={report.signals} />}
      {report.completed_tasks.length === 0 ? null : (
        <CompletedTasks completed={report.completed_tasks} />
      )}
      {report.ignored.length === 0 ? null : <Ignored ignored={report.ignored} />}
    </div>
  );
}

/**
 * What the import may still be asked: a file the report rejects whole is applied no more, and only
 * its abandonment stays offered (`import_file_accepted`, WF-INTF-0040). The contract lists no
 * commands on an import (`Import` has no `available_commands`; the project's offer is not about
 * one import), so the report itself says it: the one rule the screen reads from it.
 */
function stepsOf(entry: Import): (typeof IMPORT_STEPS)[Import["status"]] {
  const steps = IMPORT_STEPS[entry.status];
  return entry.report != null && entry.report.refusals.length > 0
    ? { ...steps, apply: false }
    : steps;
}

/** The import a report is of, what the server offers of its kind, and where the screen started. */
export interface ImportReportProps {
  readonly projectId: string;
  readonly entry: Import;
  readonly offer: CommandOffer | undefined;
  readonly start: string;
  /** Where the screen leads once the import is applied — the planning it fills, if it is one. */
  readonly then?: string | undefined;
}

/** Render the report of an import, and offer to apply or abandon it. */
export function ImportReport({ projectId, entry, offer, start, then }: ImportReportProps) {
  const t = useTranslations();
  const title = t("exchanges.report.title", { file: entry.filename });
  return (
    <section aria-label={title} className="space-y-3 rounded-md border p-3">
      <h2 className="flex items-center gap-2 text-base font-semibold">
        <FileSpreadsheet aria-hidden="true" className={ICON} />
        {title}
      </h2>
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
      {entry.report == null ? (
        <p className={MUTED}>
          {t(entry.status === "analysing" ? "exchanges.report.analysing" : "exchanges.report.none")}
        </p>
      ) : (
        <Findings report={entry.report} />
      )}
      {/* Its own commands for each import: an outcome, a confirmation open, stay with theirs. */}
      <ReportCommands
        key={entry.import_id}
        projectId={projectId}
        importId={entry.import_id}
        filename={entry.filename}
        offer={offer}
        steps={stepsOf(entry)}
        start={start}
        then={then}
      />
    </section>
  );
}
