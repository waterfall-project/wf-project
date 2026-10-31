// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The planning start date of the structure a grid of the planning reads (WF-PLA-0020,
 * `CostStructure.planning_start_on`), above the grid: the day the automatic tasks without a
 * predecessor start on, shown as the server gives it; and, where the structure lists `edit_planning`,
 * the command that changes it (`updateCostStructure`), confirmed in a form that asks the day. The
 * server judges it on the default calendar: a day without a working hour is refused
 * (`NON_WORKING_DAY`), the refusal said under the field with the working day that follows, and
 * nothing is written. Written, the tasks the server redates take their place in the grid (the page
 * is read anew), the version the structure moved on to is told to the account of the grid, which
 * counts the write among its own so that its gestures wait for it, and the date shown is the one the
 * server answered while the page read is older (the fake back keeps nothing, `MockupNotice`).
 */
"use client";

import { CalendarDays } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { useId, useState } from "react";

import { updateStructure } from "@/api/actions/nodes";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { ConfirmedCommand } from "@/components/commands/confirmed-command";
import { formatPlanningDate, isPlanningDate } from "@/i18n/format";

import type { StructurePath } from "./nodes";
import type { StructureAccount } from "./structure-version";

/** A date of planning, as the contract writes it. */
type PlanningDate = components["schemas"]["PlanningDate"];

/** What the planning start date shows and writes: the structure, its date read, its label. */
export interface PlanningStartProps {
  readonly structure: StructurePath;
  /** The date the page read (`CostStructure.planning_start_on`). */
  readonly planningStart: PlanningDate;
  /** The version of the structure the page read: a date answered with a later one prevails. */
  readonly read: number;
  /** How the screen names the structure, which a refusal and the history of the messages cite. */
  readonly label: string;
  /** The account of the writes of the grid, to which the write is counted. */
  readonly account: StructureAccount;
  /** Whether the structure lists `edit_planning`: the date can be changed. */
  readonly editable: boolean;
}

/** A date answered by a write, for the structure it was written in, with the version it moved on to. */
interface Written {
  readonly structure: string;
  readonly on: PlanningDate;
  readonly version: number;
}

/** Show the planning start date of a structure, and change it where the planning may be entered. */
export function PlanningStart({
  structure,
  planningStart,
  read,
  label,
  account,
  editable,
}: PlanningStartProps) {
  const t = useTranslations("planningGrid.planningStart");
  const helps = useTranslations("commands");
  const locale = useLocale();
  const field = useId();
  const [typed, setTyped] = useState<string>();
  const [written, setWritten] = useState<Written>();
  const ours = written?.structure === structure.structure_id ? written : undefined;
  const current = ours !== undefined && ours.version > read ? ours.on : planningStart;
  const value = typed ?? current;
  const chosen = isPlanningDate(value) ? value : undefined;
  const run = (): Promise<Outcome<{ readonly structure_lock_version: number }>> => {
    if (chosen === undefined) {
      return Promise.reject(new Error("the date is confirmed once it is a date"));
    }
    // Sent, and counted among the writes of the grid, once out of the transition that runs it.
    return Promise.resolve().then(() => {
      const write = updateStructure(structure, {
        planning_start_on: chosen,
        lock_version: account.version,
      });
      account.writing(write);
      return write;
    });
  };
  return (
    <section aria-label={t("label")} className="flex flex-wrap items-start gap-3 text-sm">
      <p className="py-1">
        {t.rich("shown", {
          date: formatPlanningDate(current, locale, "short"),
          label: (text) => <span className="font-medium">{text}</span>,
          time: (text) => <time dateTime={current}>{text}</time>,
        })}
      </p>
      {editable ? (
        <ConfirmedCommand
          offer={{ is_available: true, missing_conditions: [] }}
          label={t("change")}
          help={helps("planningStart.help")}
          icon={<CalendarDays aria-hidden="true" />}
          statement={t("statement")}
          submit={t("submit")}
          ready={chosen !== undefined && chosen !== current && !account.busy}
          names={{ [structure.structure_id]: label }}
          subject={label}
          run={run}
          done={() => t("done", { date: formatPlanningDate(value, locale, "short") })}
          onDone={(data) => {
            account.reach(data.structure_lock_version);
            if (chosen !== undefined) {
              setWritten({
                structure: structure.structure_id,
                on: chosen,
                version: data.structure_lock_version,
              });
            }
            setTyped(undefined);
          }}
        >
          <div className="space-y-1">
            <label htmlFor={field} className="block text-sm font-medium">
              {t("label")}
            </label>
            <input
              id={field}
              type="date"
              required
              value={value}
              onChange={(event) => {
                setTyped(event.target.value);
              }}
              className="h-9 rounded-md border border-input bg-background px-2 text-foreground"
            />
          </div>
        </ConfirmedCommand>
      ) : null}
    </section>
  );
}
