// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The Kanban of the start of the tasks (FBS-4.5.3, WF-RAE-0030), as the contract gives it
 * (`listStartableTasks`): a column of the tasks not started, and one of the tasks started, whose
 * remaining to commit is to re-estimate, each in the order of the answer; the column of the tasks
 * completed, which the contract now renders and the Kanban reopens, comes with EP-02/L36 (#425).
 * A task is a card: its row number and its label, its finish, the mark of a finish past the date
 * of calculation (`finish_overdue`), and, for a milestone not started whose predecessors are all
 * completed, as the API says (`predecessors_completed`), the mark that invites one to complete it,
 * which nothing does by itself. A task is started or it is not: no percentage
 * shows, nor is entered (US-0230). Starting or completing a task is a command of the epic of the
 * actual costs and of the progress, not of the mock-up: no card offers one.
 *
 * A component of the server: nothing of it crosses to the browser but what it renders.
 */
import { CalendarX2, Diamond, Flag } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";

import type { operations } from "@/api/generated/schema";
import { formatPlanningDate } from "@/i18n/format";

/** The answer of `listStartableTasks`: the tasks not started, started and completed. */
export type StartableTasks =
  operations["listStartableTasks"]["responses"][200]["content"]["application/json"];

/** A task of the Kanban, as the API reads it: a task not started says if its predecessors are. */
type KanbanTask = StartableTasks["started"][number] | StartableTasks["not_started"][number];

/** The columns of the Kanban, in their order: the key of the answer, and that of its title. */
const COLUMNS = [
  ["not_started", "notStarted"],
  ["started", "started"],
] as const satisfies readonly (readonly [keyof StartableTasks, string])[];

/** A card of the Kanban: a task, and whether it is a milestone to complete, as the API says. */
function Card({ node }: { readonly node: KanbanTask }) {
  const t = useTranslations("kanban");
  const locale = useLocale();
  const task = node.task;
  const finish = task?.finish?.date;
  const milestone = task?.is_milestone === true;
  const due = milestone && "predecessors_completed" in node && node.predecessors_completed;
  return (
    <li className="space-y-1 rounded-md border bg-card p-2 text-sm">
      <p className="flex items-baseline gap-2">
        <span className="tabular-nums text-muted-foreground">{node.row_number}</span>
        {milestone ? (
          <Diamond role="img" aria-label={t("milestone")} className="size-3.5 shrink-0">
            <title>{t("milestone")}</title>
          </Diamond>
        ) : null}
        <span className="font-medium">{task?.label}</span>
      </p>
      {finish === undefined ? null : (
        <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
          {t("finish", { date: formatPlanningDate(finish, locale, "short") })}
          {task?.finish_overdue === true ? (
            <CalendarX2 role="img" aria-label={t("finishOverdue")} className="size-3.5">
              <title>{t("finishOverdue")}</title>
            </CalendarX2>
          ) : null}
        </p>
      )}
      {due ? (
        <p className="flex items-center gap-1.5 text-xs font-medium">
          <Flag aria-hidden="true" className="size-3.5 shrink-0" />
          {t("milestoneDue")}
        </p>
      ) : null}
    </li>
  );
}

/** Render the Kanban of the start of the tasks: its two columns, each a list of cards. */
export function Kanban({ tasks }: { readonly tasks: StartableTasks }) {
  const t = useTranslations("kanban");
  return (
    <div className="grid gap-4 sm:grid-cols-2">
      {COLUMNS.map(([key, title]) => {
        const cards = tasks[key];
        return (
          <section key={key} aria-label={t(title)} className="space-y-2">
            <h2 className="text-sm font-semibold">{t(title)}</h2>
            {cards.length === 0 ? (
              <p className="text-sm text-muted-foreground">{t("empty")}</p>
            ) : (
              <ul className="space-y-2">
                {cards.map((node) => (
                  <Card key={node.node_id} node={node} />
                ))}
              </ul>
            )}
          </section>
        );
      })}
    </div>
  );
}
