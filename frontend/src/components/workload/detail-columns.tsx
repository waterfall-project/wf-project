// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The configuration of the grid of the detail of the workload (WF-DEV-0090, US-2040): a tree from
 * the role to the task, read only, in the order of the API — no header sorts, nothing is searched
 * —; the label of each row under the icon of its nature, a task's leading to its row in the planning
 * grid; the number of the task in the plan, its start, its finish and its hours; then one column for
 * each month of the plan, headed by the month, the totals of the months at the foot as the API sums
 * them. Each column with its definition, which the grid and the help of its screen both read.
 *
 * Neither server nor client: the grid renders it in the browser; `help/read.ts` reads its columns
 * on the server, their titles and definitions only.
 */
import { ClipboardList, Users } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";

import type { GridColumn, GridConfig } from "@/components/grid/columns";

import { DETAIL_GRID_KEY, type DetailRow, type DetailTotals } from "./detail-rows";

/** A column of the grid of the detail: it sorts nothing. */
type DetailColumn = GridColumn<DetailRow, never, DetailTotals>;

/** The classes of the link of a task: the cell is the stop of the grid, the link follows on Enter. */
const LINK = "block truncate underline-offset-2 hover:underline";

/** The icon of the nature of a row, named for it: a role, a task. */
function DetailNature({ kind }: { readonly kind: DetailRow["kind"] }) {
  const t = useTranslations();
  const Icon = kind === "role" ? Users : ClipboardList;
  return (
    <Icon
      role="img"
      aria-label={kind === "role" ? t("workload.role") : t("rowNature.task")}
      className="size-3.5 shrink-0 text-muted-foreground"
    />
  );
}

/**
 * The label of a row: a task the session may follow to the planning grid leads there, out of the
 * order of tabulation — the grid is one stop, and Enter on the cell follows the link.
 */
function DetailLabel({ row }: { readonly row: DetailRow }) {
  return row.href === undefined ? (
    row.label
  ) : (
    <Link href={row.href} tabIndex={-1} className={LINK}>
      {row.label}
    </Link>
  );
}

/** The column of a month: its hours in each row, as the API gives them, its total at the foot. */
function monthColumn(month: string, heading: string): DetailColumn {
  return {
    key: `month_${month}`,
    label: "month",
    heading,
    help: "workloadDetail.month",
    format: "decimal",
    width: 96,
    value: (row) => row.months[month],
    total: (totals) => totals[month],
  };
}

/**
 * The grid of the detail, a column for each month of the plan, headed as `heading` writes the month
 * in the language of the interface.
 */
export function detailGrid(
  months: readonly string[],
  heading: (month: string) => string,
): GridConfig<DetailRow, never, DetailTotals> {
  return {
    key: DETAIL_GRID_KEY,
    name: "workloadDetail",
    searched: false,
    sorts: false,
    rowKey: (row) => row.key,
    tree: {
      level: (row) => (row.kind === "role" ? 1 : 2),
      nature: (row) => <DetailNature kind={row.kind} />,
      emphasis: (row) => (row.kind === "role" ? "strong" : undefined),
      parent: (row) => row.parent,
    },
    columns: [
      {
        key: "label",
        label: "label",
        help: "workloadDetail.label",
        format: "text",
        width: 280,
        pinned: true,
        value: (row) => row.label,
        render: (row) => <DetailLabel row={row} />,
      },
      {
        key: "task_row",
        label: "rowNumber",
        help: "workloadDetail.rowNumber",
        format: "text",
        align: "end",
        width: 64,
        value: (row) => row.rowNumber,
      },
      {
        key: "start",
        label: "startDate",
        help: "workloadDetail.start",
        format: "date",
        width: 96,
        value: (row) => row.start,
      },
      {
        key: "finish",
        label: "finishDate",
        help: "workloadDetail.finish",
        format: "date",
        width: 96,
        value: (row) => row.finish,
      },
      {
        key: "hours",
        label: "hours",
        help: "workloadDetail.hours",
        format: "decimal",
        width: 96,
        value: (row) => row.hours,
      },
      ...months.map((month) => monthColumn(month, heading(month))),
    ],
  };
}
