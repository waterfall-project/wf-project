// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The two tables of a report that may run to thousands of rows — the lines rejected, the
 * differences with the existing data (WF-INTF-0080) —, each rendered by windows: its first 200
 * rows, the number of those left said under it, and the offer to show them all (US-3280, FCO-06
 * of #4425). The count is that of the report received, in the order received: the front counts and
 * sorts nothing else. Client components, which the server renders too, and the rows go whole in
 * the RSC payload: the window bounds the DOM, not the payload.
 */
"use client";

import { useFormatter, useLocale, useMessages, useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";

import type { components } from "@/api/generated/schema";
import type { RowDifference } from "@/components/grid/columns";
import { DiffMark } from "@/components/grid/diff-mark";
import { NODE_COLUMNS, type NodeColumn } from "@/components/grid/nodes";
import { CELL, ListTable } from "@/components/projects/project-tables";
import { Button } from "@/components/ui/button";
import { TableCell, TableRow } from "@/components/ui/table";
import type { Catalogue } from "@/i18n/catalogues";
import { formatDecimal } from "@/i18n/format";
import { problemMessage } from "@/i18n/problem";

type Report = components["schemas"]["ImportReport"];
type Difference = Report["differences"][number];
type DifferenceField = NonNullable<Difference["fields"]>[number];

/** The heading of a part of a report. */
const HEADING = "text-sm font-semibold";

/** How many rows of a table of a report are drawn before the user asks for the others. */
const WINDOW = 200;

/**
 * The rows of a table that are drawn, and what is left to say or to offer. A table not limited
 * draws them all and says nothing of it: `all` is only the answer to the button pressed.
 */
function useWindowed<Row>(rows: readonly Row[], limited: boolean) {
  const [all, setAll] = useState(false);
  return {
    drawn: all || !limited ? rows : rows.slice(0, WINDOW),
    left: limited && !all ? Math.max(0, rows.length - WINDOW) : 0,
    all,
    showAll: () => {
      setAll(true);
    },
  };
}

/**
 * What a table says of its rows left out, and the offer to draw them: nothing while the table holds
 * no more than its window. Once all are drawn, it says so — the button that was pressed goes, and
 * the focus goes to that sentence rather than to the page.
 */
function RowsLeft({
  total,
  left,
  all,
  onAll,
  titleId,
}: {
  readonly titleId: string;
  readonly total: number;
  readonly left: number;
  readonly all: boolean;
  readonly onAll: () => void;
}) {
  const t = useTranslations("exchanges.report");
  const said = useRef<HTMLParagraphElement>(null);
  useEffect(() => {
    if (all) {
      said.current?.focus();
    }
  }, [all]);
  if (all) {
    return (
      <p ref={said} tabIndex={-1} role="status" className="text-sm text-muted-foreground">
        {t("allShown", { count: total })}
      </p>
    );
  }
  if (left === 0) {
    return null;
  }
  return (
    <div className="flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
      <p>{t("rowsLeft", { count: left })}</p>
      <Button type="button" variant="outline" size="sm" onClick={onAll} aria-describedby={titleId}>
        {t("showAll")}
      </Button>
    </div>
  );
}

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

/**
 * The lines of the file rejected, each by its place — the tab that bears it, as the file names it,
 * when the file has tabs (ANNEXE B, WF-INTF-0180), and its row — and its motive, in the order
 * received. A file without tabs, a planning MS Project, shows no column of tabs.
 */
export function Rejections({ rejected }: { readonly rejected: Report["rejected"] }) {
  const t = useTranslations("exchanges.report");
  const locale = useLocale();
  const messages = useMessages();
  const rows = useWindowed(rejected, true);
  const titleId = useId();
  const tabbed = rejected.some(({ sheet }) => sheet != null);
  return (
    <div className="space-y-1">
      <h3 id={titleId} className={HEADING}>
        {t("rejected", { count: rejected.length })}
      </h3>
      {rejected.length === 0 ? null : (
        <ListTable
          label={t("rejectedTable")}
          columns={tabbed ? [t("sheet"), t("row"), t("motive")] : [t("row"), t("motive")]}
        >
          {rows.drawn.map((line, index) => (
            <TableRow key={`${line.sheet ?? ""}-${String(line.row)}-${String(index)}`}>
              {tabbed ? <TableCell className={CELL}>{line.sheet}</TableCell> : null}
              <TableCell className={`${CELL} tabular-nums`}>
                {formatDecimal(String(line.row), locale)}
              </TableCell>
              <TableCell className={CELL}>{problemMessage(line, { locale, messages })}</TableCell>
            </TableRow>
          ))}
        </ListTable>
      )}
      <RowsLeft
        titleId={titleId}
        total={rejected.length}
        left={rows.left}
        all={rows.all}
        onAll={rows.showAll}
      />
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
  limited = false,
}: {
  readonly differences: Report["differences"];
  /**
   * Whether the table is drawn by windows (`WINDOW` rows, the rest on demand): the report of an
   * import is, which may run to thousands of rows; the report of an amendment or of an occurrence,
   * read whole to be confirmed, is not.
   */
  readonly limited?: boolean;
  /** Whether each change bears the mark of the diff of a grid, `+`, `-`, `M` (US-0510). */
  readonly marks?: boolean;
}) {
  const t = useTranslations();
  const format = useFormatter();
  const rows = useWindowed(differences, limited);
  const titleId = useId();
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
      <h3 id={titleId} className={HEADING}>
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
          {rows.drawn.map((difference, index) => (
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
      <RowsLeft
        titleId={titleId}
        total={differences.length}
        left={rows.left}
        all={rows.all}
        onAll={rows.showAll}
      />
    </div>
  );
}
