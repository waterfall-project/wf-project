// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the report says of the calendar gap of an MS Project schedule (WF-INTF-0080, WF-INTF-0040,
 * WF-PLA-0160): that the days of the project calendar of the file, or its constants, differ from
 * those of the installation — the hours per day on either side, day by day, and the working times
 * of the file —, each task whose own calendar differs from its applicable Waterfall calendar, named,
 * and that the calendar of the file is ignored, never imported. The choice of the rule is
 * `DurationRule`'s.
 */
import { useFormatter, useLocale, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { CELL, ListTable } from "@/components/projects/project-tables";
import { TableCell, TableRow } from "@/components/ui/table";
import { formatDecimal } from "@/i18n/format";

type Gap = components["schemas"]["ImportCalendarGap"];
type Weekly = components["schemas"]["WeeklyHours"];

const DAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const satisfies readonly (keyof Weekly)[];

const HEADING = "text-sm font-semibold";

/** The hours per day of a week, each day by its short name, in the order of the week. */
function WeekHours({ hours }: { readonly hours: Weekly }) {
  const t = useTranslations("exchanges.report.calendarGap");
  const locale = useLocale();
  return DAYS.map((day) => `${t(`daysShort.${day}`)} ${formatDecimal(hours[day], locale)}`).join(
    ", ",
  );
}

/** Render the calendar gap of the report. */
export function CalendarGap({ gap }: { readonly gap: Gap }) {
  const t = useTranslations("exchanges.report.calendarGap");
  const format = useFormatter();
  const locale = useLocale();
  const { project_calendar: file, installation_calendar: installation } = gap;
  return (
    <div className="space-y-2">
      <h3 className={HEADING}>{t("title")}</h3>
      <p className="text-sm">{t("lead")}</p>
      <ListTable
        label={t("daysTable")}
        columns={[
          t("day"),
          t("fileTimes", { calendar: file.name ?? t("unnamed") }),
          t("fileHours"),
          t("installationHours", { calendar: installation.label }),
        ]}
      >
        {DAYS.map((day) => (
          <TableRow key={day}>
            <TableCell className={CELL}>{t(`days.${day}`)}</TableCell>
            <TableCell className={CELL}>
              {file.working_times[day].length === 0
                ? t("noWork")
                : format.list(
                    file.working_times[day].map((time) => `${time.from}–${time.to}`),
                    { type: "conjunction" },
                  )}
            </TableCell>
            <TableCell className={`${CELL} tabular-nums`}>
              {formatDecimal(file.weekly_hours[day], locale)}
            </TableCell>
            <TableCell className={`${CELL} tabular-nums`}>
              {formatDecimal(installation.weekly_hours[day], locale)}
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
      <h4 className={HEADING}>{t("tasks", { count: gap.tasks.length })}</h4>
      {gap.tasks.length === 0 ? null : (
        <ListTable
          label={t("tasksTable")}
          columns={[t("task"), t("taskCalendar"), t("taskFileHours"), t("taskWaterfallHours")]}
        >
          {gap.tasks.map((task, index) => (
            <TableRow key={`${task.lineage_id ?? "new"}-${String(index)}`}>
              <TableCell className={CELL}>{task.label}</TableCell>
              <TableCell className={CELL}>{task.file_calendar.name ?? t("unnamed")}</TableCell>
              <TableCell className={CELL}>
                <WeekHours hours={task.file_calendar.weekly_hours} />
              </TableCell>
              <TableCell className={CELL}>
                <WeekHours hours={task.weekly_hours} />
              </TableCell>
            </TableRow>
          ))}
        </ListTable>
      )}
      <p role="note" className="text-sm text-muted-foreground">
        {t("ignored")}
      </p>
    </div>
  );
}
