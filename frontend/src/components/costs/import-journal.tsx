// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The journal of the imports of actual costs (WF-CRE-0050), a page of it, the most recent first as
 * the server gives it: of each import, its date in the local time of the workstation, its author,
 * the period extracted and the counts of the lines created, updated and rejected — figures the
 * server counted, in the format of the language. The way through its pages, when the server holds
 * more than one; that it is empty, when no import was ever made. A region named by its label, as
 * the totals and the filters are: no identifier drawn on the server (#251).
 */
import { History } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { KeptListSize } from "@/components/grid/kept-list-size";
import { ListPages } from "@/components/grid/list-pages";
import type { GridPreferences } from "@/components/grid/settings";
import { LocalTime } from "@/components/local-time";
import { Actor, CELL, ICON, ListTable } from "@/components/projects/project-tables";
import { TableCell, TableRow } from "@/components/ui/table";
import { formatDecimal, formatPlanningDate } from "@/i18n/format";

import { COST_IMPORT_GRID_KEY, IMPORTS_ADDRESS, IMPORTS_LIST } from "./address";
import type { ListPage } from "./cost-grid";

/** An entry of the journal, as the contract gives it. */
export type CostImport = components["schemas"]["CostImport"];

/** The period an import extracted, in words: its bounds the API gives, or that it gives none. */
function Period({ entry }: { readonly entry: CostImport }) {
  const t = useTranslations("actualCosts.imports");
  const locale = useLocale();
  const from = entry.period_from ?? null;
  const to = entry.period_to ?? null;
  const date = (value: string) => formatPlanningDate(value, locale, "short");
  if (from !== null && to !== null) {
    return t("periodRange", { from: date(from), to: date(to) });
  }
  if (from !== null) {
    return t("periodFrom", { from: date(from) });
  }
  return to === null ? t("periodUnknown") : t("periodTo", { to: date(to) });
}

/** Render a page of the journal of the imports, and the way through its pages. */
export function ImportJournal({
  imports,
  page,
  preferences,
}: {
  readonly imports: readonly CostImport[];
  readonly page: ListPage;
  /** What the account kept for the journal, whose size of pages it records. */
  readonly preferences?: GridPreferences | undefined;
}) {
  const t = useTranslations("actualCosts.imports");
  const locale = useLocale();
  const count = (value: number) => formatDecimal(String(value), locale);
  return (
    <section aria-label={t("title")} className="space-y-2">
      <h2 className="flex items-center gap-2 text-base font-semibold">
        <History aria-hidden="true" className={ICON} />
        {t("title")}
      </h2>
      {page.total === 0 ? <p className="text-sm text-muted-foreground">{t("none")}</p> : null}
      {imports.length === 0 ? null : (
        <ListTable
          label={t("title")}
          columns={[
            t("importedAt"),
            t("actor"),
            t("period"),
            t("created"),
            t("updated"),
            t("rejected"),
          ]}
        >
          {imports.map((entry) => (
            <TableRow key={entry.cost_import_id}>
              <TableCell className={CELL}>
                <LocalTime value={entry.imported_at} />
              </TableCell>
              <TableCell className={CELL}>
                <Actor actor={entry.actor} />
              </TableCell>
              <TableCell className={CELL}>
                <Period entry={entry} />
              </TableCell>
              <TableCell className={`${CELL} text-right tabular-nums`}>
                {count(entry.created_count)}
              </TableCell>
              <TableCell className={`${CELL} text-right tabular-nums`}>
                {count(entry.updated_count)}
              </TableCell>
              <TableCell className={`${CELL} text-right tabular-nums`}>
                {count(entry.rejected_count)}
              </TableCell>
            </TableRow>
          ))}
        </ListTable>
      )}
      <ListPages
        list={IMPORTS_LIST}
        texts="actualCosts.pages.imports"
        title={t("title")}
        page={page}
        shown={imports.length}
      />
      <KeptListSize
        gridKey={COST_IMPORT_GRID_KEY}
        address={IMPORTS_ADDRESS}
        preferences={preferences}
      />
    </section>
  );
}
