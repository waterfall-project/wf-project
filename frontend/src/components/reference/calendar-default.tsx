// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The default calendar in its grid (WF-REF-0120): marked by an icon and its words; and the designation
 * of another as the calendar lists it (`CalendarCommand.set_default`, EP-14/L43g, WF-IHM-0090) —
 * absent, nothing, the server listing it only to a session that may modify the settings of the
 * resources, and on no calendar by default already; available, by `setDefaultCalendar` from the
 * version read, the server withdrawing the designation from the one before — the page is read anew,
 * and the row shows the answer meanwhile (`useAnswered`); unavailable — a deactivated calendar, which
 * lacks `calendar_active` —, presented `aria-disabled` and described by its condition, a press saying
 * it in the region of the list without asking anything (`UnavailableCellCommand`). The front deduces
 * nothing of the state of the row. A refusal of the server — the calendar deactivated meanwhile (409,
 * `calendar_active`), the version stale (412), with the offer to read the page anew — is told above
 * the list (`useRowCommand`).
 */
"use client";

import { CalendarCheck } from "lucide-react";
import { useTranslations } from "next-intl";

import { designateDefaultCalendar } from "@/api/actions/reference";
import { findOffer } from "@/components/commands/offer";
import { ICON } from "@/components/projects/project-tables";

import { CellCommand, UnavailableCellCommand } from "./cell-command";
import { useRowCommand } from "./commands";
import { useListReport } from "./reactivation";
import type { Calendar } from "./resource-grids";

/** The command that designates a calendar by default, named after it. */
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
 * The mark of the default calendar, an icon and its words; on another, its designation as it lists
 * it — available, unavailable with its condition, or absent.
 */
export function DefaultCalendarCell({ calendar }: { readonly calendar: Calendar }) {
  const t = useTranslations("reference.calendars");
  const list = useListReport();
  if (calendar.is_default) {
    return (
      <span className="inline-flex items-center gap-1.5">
        <CalendarCheck aria-hidden="true" className={ICON} />
        {t("isDefault")}
      </span>
    );
  }
  const offer = findOffer(calendar.available_commands, "set_default");
  if (offer === undefined) {
    return null;
  }
  return offer.is_available ? (
    <DesignateCommand calendar={calendar} />
  ) : (
    <UnavailableCellCommand
      name={t("designate", { name: calendar.label })}
      offer={offer}
      onPress={() => {
        list?.tell(calendar.label, offer, "set_default");
      }}
    >
      <CalendarCheck aria-hidden="true" />
      {t("designateShort")}
    </UnavailableCellCommand>
  );
}
