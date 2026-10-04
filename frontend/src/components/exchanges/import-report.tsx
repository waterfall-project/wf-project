// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The report of an import, as `getImport` gives it (WF-INTF-0080): the file, its kind and where
 * the import stands, when it was opened and until when its report applies; then, once analysed,
 * the lines read, the reasons that ask for an explicit confirmation, each line rejected by its
 * place in the file and its motive, and each difference with the existing data. Every sentence
 * is the catalogue's, written from the codes the API gives (WF-ARC-0110): a motive from its code
 * and parameters, as a refusal is; the label of a line, which comes from the file or the project,
 * as it is. The front counts, sorts and filters nothing: the lists are in the order received.
 * Under it, its application and its abandonment (`ReportCommands`).
 */
import { FileSpreadsheet } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import type { CommandOffer } from "@/components/commands/offer";
import { LocalTime } from "@/components/local-time";
import { CELL, ICON, ListTable } from "@/components/projects/project-tables";
import { TableCell, TableRow } from "@/components/ui/table";
import { formatDecimal } from "@/i18n/format";
import { problemMessage } from "@/i18n/problem";

import { IMPORT_STEPS } from "./offers";
import { ReportCommands } from "./report-commands";

type Import = components["schemas"]["Import"];
type Report = components["schemas"]["ImportReport"];

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

/** The differences with the existing data, each by its change, its object and its label. */
function Differences({ differences }: { readonly differences: Report["differences"] }) {
  const t = useTranslations();
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
          ]}
        >
          {differences.map((difference, index) => (
            <TableRow key={`${difference.lineage_id ?? "new"}-${String(index)}`}>
              <TableCell className={CELL}>
                {t(`enums.ImportDifference.change.${difference.change}`)}
              </TableCell>
              <TableCell className={CELL}>
                {t(`enums.ImportDifference.target.${difference.target}`)}
              </TableCell>
              <TableCell className={CELL}>
                {difference.label ?? t("exchanges.report.unnamed")}
              </TableCell>
            </TableRow>
          ))}
        </ListTable>
      )}
    </div>
  );
}

/** What the analysis found: lines read, reasons to confirm, lines rejected, differences. */
function Findings({ report }: { readonly report: Report }) {
  const t = useTranslations();
  const reasons = report.requires_confirmation_reasons ?? [];
  return (
    <div className="space-y-3">
      <p className="text-sm">{t("exchanges.report.read", { count: report.read_count })}</p>
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
      <Rejections rejected={report.rejected} />
      <Differences differences={report.differences} />
    </div>
  );
}

/** The import a report is of, what the server offers of its kind, and where the screen started. */
export interface ImportReportProps {
  readonly projectId: string;
  readonly entry: Import;
  readonly offer: CommandOffer | undefined;
  readonly start: string;
}

/** Render the report of an import, and offer to apply or abandon it. */
export function ImportReport({ projectId, entry, offer, start }: ImportReportProps) {
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
        <dt className="text-muted-foreground">{t("exchanges.report.expiresAt")}</dt>
        <dd>
          <LocalTime value={entry.expires_at} />
        </dd>
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
        steps={IMPORT_STEPS[entry.status]}
        start={start}
      />
    </section>
  );
}
