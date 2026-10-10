// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The default calendar in its grid (WF-REF-0120): marked by an icon and its words; and, for a session
 * that may modify the settings of the resources, a calendar active and not by default designated from
 * its row (`setDefaultCalendar`, EP-02/L43b), the server withdrawing the designation from the one
 * before — the page is read anew, and the row shows the answer meanwhile (`useAnswered`). The contract
 * lists no command for it (`ReferenceCommand`): the front offers it on the state the row reads, by the
 * one rule the contract gives — a calendar active, not by default already.
 */
"use client";

import { CalendarCheck } from "lucide-react";
import { useTranslations } from "next-intl";

import { designateDefaultCalendar } from "@/api/actions/reference";
import { ICON } from "@/components/projects/project-tables";

import { CellCommand } from "./cell-command";
import { useRowCommand } from "./commands";
import type { Calendar } from "./resource-grids";

/** The command that designates an active calendar by default, named after it. */
function DesignateCommand({ calendar }: { readonly calendar: Calendar }) {
  const t = useTranslations("reference");
  const [pending, run] = useRowCommand(`designate calendar ${calendar.calendar_id}`, {});
  return (
    <CellCommand
      aria-label={t("calendars.designate", { name: calendar.label })}
      aria-busy={pending}
      onClick={() => {
        run(
          async () => {
            const outcome = await designateDefaultCalendar(
              calendar.calendar_id,
              calendar.lock_version,
            );
            return outcome.kind === "done" ? { kind: "done", data: [outcome.data] } : outcome;
          },
          (rows) => t("form.designated", { name: rows[0]?.label ?? calendar.label }),
        );
      }}
    >
      <CalendarCheck aria-hidden="true" />
      {t("calendars.designateShort")}
    </CellCommand>
  );
}

/**
 * The mark of the default calendar, an icon and its words; for a session that may modify the settings
 * of the resources, the designation of a calendar active and not by default.
 */
export function DefaultCalendarCell({
  calendar,
  editable,
}: {
  readonly calendar: Calendar;
  readonly editable: boolean;
}) {
  const t = useTranslations("reference.calendars");
  if (calendar.is_default) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <CalendarCheck aria-hidden="true" className={ICON} />
        {t("isDefault")}
      </span>
    );
  }
  return editable && calendar.is_active ? <DesignateCommand calendar={calendar} /> : null;
}
