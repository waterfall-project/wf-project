// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The cells of the grid of the remaining to commit that show more than a value formatted: the mark
 * of a task started whose finish is past the date of calculation (WF-RAE-0040), which the server
 * says (`finish_overdue`) — never deduced here from the finish and a date. It is a mark of its own,
 * an icon named by the catalogue, never a zone of the scale of signals, which the server alone
 * gives (`Signal`, WF-ARC-0020).
 *
 * The mark of the own lines still open (`awaiting_own_lines`, WF-PLA-0040, WF-IHM-0070) is of the
 * same kind: the server says it of a summary task, whose subordinates are all completed, and the
 * grid marks the task and its own lines but the provisions. A line says nothing of its task, so the
 * set of the tasks so marked is read once from the rows the grid shows (`OwnLinesOpen`, around the
 * grid) and handed to the cells by a context — never the rows themselves to each cell.
 */
"use client";

import { CalendarX2, ListTodo } from "lucide-react";
import { useTranslations } from "next-intl";
import { createContext, type ReactNode, use, useMemo } from "react";

/** Render the mark of a task whose finish is past; nothing for the others, nor for a line. */
export function OverdueCell({
  node,
}: {
  readonly node: { readonly task?: { readonly finish_overdue: boolean } | null };
}) {
  const t = useTranslations("remainingGrid");
  if (node.task?.finish_overdue !== true) {
    return null;
  }
  return (
    <CalendarX2 role="img" aria-label={t("finishOverdue")} className="inline size-3.5">
      <title>{t("finishOverdue")}</title>
    </CalendarX2>
  );
}

/** The tasks the server says wait for their own lines, by the identifier of their node. */
const OpenTasks = createContext<ReadonlySet<string>>(new Set());

/** The rows `OwnLinesOpen` reads: a task says it, a line names the task it is under. */
interface OwnLinesRow {
  readonly node_id: string;
  readonly parent_id?: string | null | undefined;
  readonly task?: { readonly awaiting_own_lines?: boolean | undefined } | null;
  readonly estimate_line?: { readonly is_computed: boolean } | null;
}

/**
 * Hand the cells the tasks that wait for their own lines, as the rows shown say it: nothing is
 * deduced from the subordinates of a task (WF-ARC-0020), the boolean of the server is read.
 */
export function OwnLinesOpen({
  rows,
  children,
}: {
  readonly rows: readonly OwnLinesRow[];
  readonly children: ReactNode;
}) {
  const open = useMemo(
    () =>
      new Set(
        rows.filter((row) => row.task?.awaiting_own_lines === true).map((row) => row.node_id),
      ),
    [rows],
  );
  return <OpenTasks value={open}>{children}</OpenTasks>;
}

/**
 * Render the mark of the own lines open, an icon and its text: on a task the server says waits for
 * its own lines, and on each of its lines but a provision; nothing for any other row.
 */
export function OwnLinesCell({ node }: { readonly node: OwnLinesRow }) {
  const t = useTranslations("remainingGrid");
  const open = use(OpenTasks);
  const marked =
    node.task?.awaiting_own_lines === true ||
    (node.estimate_line?.is_computed === false &&
      node.parent_id !== null &&
      node.parent_id !== undefined &&
      open.has(node.parent_id));
  if (!marked) {
    return null;
  }
  return (
    <span className="inline-flex items-center gap-1 text-xs font-medium">
      <ListTodo aria-hidden="true" className="size-3.5 shrink-0" />
      {t("ownLinesOpen")}
    </span>
  );
}
