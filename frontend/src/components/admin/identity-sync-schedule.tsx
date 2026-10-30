// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The periodicity of the reading of the accounts of the identity provider, on the screen of the
 * accounts (US-0703, WF-ADM-0070): what the server reads of it — on or suspended, how often, on which
 * day, at what time in universal time — and, to a session that may modify the accounts (`users.write`),
 * its form, in the dialog of the forms of the reference data (`ReferenceForm`).
 *
 * The form writes the schedule whole (`setIdentitySyncSchedule` is a `PUT`), from the version it
 * opened on, as the schedule of the backups does (`BackupScheduleSection`): the time is entered in
 * universal time, and the local time it stands for today is said beside it. The answer takes the place
 * of what the screen shows as long as it is newer than the schedule read (`lock_version`), and the page
 * is read anew; the command that opens the form waits while a write of a dialog closed is under way
 * (#661). A refusal by field is said at its field, any other under the form. Every prop is data
 * (défaut n° 12 de `typescript.md`).
 */
"use client";

import { CalendarClock } from "lucide-react";
import { useTranslations } from "next-intl";
import { useId, useRef, useState } from "react";

import { setIdentitySyncSchedule } from "@/api/actions/users";
import type { components } from "@/api/generated/schema";
import { nextWeekday, WEEKDAYS } from "@/components/admin/backup-schedule";
import { UNAVAILABLE } from "@/components/commands/offer";
import { useSaid } from "@/components/notices/said";
import { Reactivations } from "@/components/reference/reactivation";
import {
  type Draft,
  type FormField,
  ReferenceForm,
  WritingNote,
} from "@/components/reference/reference-form";
import { Button } from "@/components/ui/button";
import { localTimeOfDay } from "@/i18n/format";

type IdentitySyncSchedule = components["schemas"]["IdentitySyncSchedule"];
type Frequency = IdentitySyncSchedule["frequency"];

/**
 * Every frequency of the contract, in the order of its enumeration: one the contract adds fails the
 * type check until it is here.
 */
const EVERY_FREQUENCY: Readonly<Record<Frequency, number>> = { daily: 0, weekly: 1 };

/** The frequencies a schedule may have, in the order of the contract. */
const FREQUENCIES = Object.keys(EVERY_FREQUENCY) as readonly Frequency[];

/** The fields of the form, by the pointer of the contract each writes, without its first slash. */
const ENABLED = "is_enabled";
const FREQUENCY = "frequency";
const WEEKDAY = "weekday";
const AT = "at_time";

/** The schedule as the screen states it: state, frequency, day and time in universal time. */
export function IdentitySyncScheduleFacts({
  schedule,
}: {
  readonly schedule: IdentitySyncSchedule;
}) {
  const t = useTranslations("admin.schedule");
  const frequencies = useTranslations("enums.IdentitySyncSchedule.frequency");
  const weekday =
    schedule.frequency === "weekly" ? WEEKDAYS[(schedule.weekday ?? 0) - 1] : undefined;
  const facts: (readonly [string, string])[] = [
    [t("state"), schedule.is_enabled ? t("enabled") : t("disabled")],
    [t("frequency"), frequencies(schedule.frequency)],
  ];
  if (weekday !== undefined) {
    facts.push([t("weekday"), t(`weekdays.${weekday}`)]);
  }
  facts.push([t("at"), t("universalTime", { time: schedule.at_time })]);
  return (
    <dl className="grid w-fit grid-cols-[auto_auto] gap-x-6 gap-y-1">
      {facts.map(([term, value]) => (
        <div key={term} className="contents">
          <dt className="text-muted-foreground">{term}</dt>
          <dd>{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** What the form starts from: the schedule as the screen shows it. */
function draftOf(schedule: IdentitySyncSchedule): Draft {
  return {
    [ENABLED]: String(schedule.is_enabled),
    [FREQUENCY]: schedule.frequency,
    [WEEKDAY]: schedule.weekday === null ? "" : String(schedule.weekday),
    [AT]: schedule.at_time,
  };
}

/**
 * The schedule the form writes, whole, from the values checked and the version it opened on: the day
 * of a weekly schedule alone, none otherwise.
 */
function scheduleOf(values: Draft, lockVersion: number): IdentitySyncSchedule {
  // The field offers the two frequencies alone: any value but the weekly one is the daily one.
  const weekly = values[FREQUENCY] === "weekly";
  return {
    is_enabled: values[ENABLED] === "true",
    frequency: weekly ? "weekly" : "daily",
    at_time: values[AT] ?? "",
    weekday: weekly ? Number(values[WEEKDAY]) : null,
    lock_version: lockVersion,
  };
}

/** The form of the schedule, opened on a version of it, at an instant that dates its local time. */
interface Opened {
  readonly schedule: IdentitySyncSchedule;
  readonly at: Date;
  readonly opening: number;
}

/** The form that sets the schedule whole, from the version it opened on. */
function ScheduleForm({
  opened: { schedule, at },
  onDone,
  onWriting,
  onClose,
  onClosed,
}: {
  readonly opened: Opened;
  readonly onDone: (answer: IdentitySyncSchedule) => void;
  readonly onWriting: (writing: boolean) => void;
  readonly onClose: () => void;
  readonly onClosed: () => void;
}) {
  const t = useTranslations("admin.schedule");
  const s = useTranslations("admin.identitySync.schedule");
  const frequencies = useTranslations("enums.IdentitySyncSchedule.frequency");
  /** The local time a time typed stands for, said beside it (the local day too for a weekly one). */
  const localTime = (draft: Draft) => {
    const weekday = Number(draft[WEEKDAY]);
    const weekly = draft[FREQUENCY] === "weekly" && weekday >= 1 && weekday <= 7;
    const local = localTimeOfDay(draft[AT] ?? "", weekly ? nextWeekday(at, weekday) : at);
    if (local === undefined) {
      return undefined;
    }
    if (!weekly) {
      return t("form.localTime", { time: local.time });
    }
    const day = WEEKDAYS[(weekday - 1 + local.shift + 7) % 7] ?? "monday";
    return t("form.localWeekTime", { time: local.time, day });
  };
  const fields: FormField[] = [
    {
      name: ENABLED,
      label: t("state"),
      control: "choice",
      required: true,
      choices: [
        ["true", t("enabled")],
        ["false", t("disabled")],
      ],
    },
    {
      name: FREQUENCY,
      label: t("frequency"),
      control: "choice",
      required: true,
      choices: FREQUENCIES.map((frequency) => [frequency, frequencies(frequency)] as const),
    },
    {
      name: WEEKDAY,
      label: t("weekday"),
      control: "choice",
      // The day of a weekly schedule alone.
      required: (draft) => draft[FREQUENCY] === "weekly",
      none: t("form.noWeekday"),
      choices: WEEKDAYS.map((day, index) => [String(index + 1), t(`weekdays.${day}`)] as const),
      note: s("weekdayNote"),
    },
    {
      name: AT,
      label: t("form.at"),
      control: "time",
      required: true,
      note: localTime,
      invalid: t("form.atInvalid"),
    },
  ];
  return (
    <ReferenceForm<IdentitySyncSchedule>
      kind="identity_sync_schedule"
      title={s("modify")}
      hint={s("hint")}
      creating={false}
      fields={fields}
      initial={draftOf(schedule)}
      ask={(values) => setIdentitySyncSchedule(scheduleOf(values, schedule.lock_version))}
      target="set identity_sync_schedule"
      answering={(answer) => answer}
      onDone={onDone}
      onWriting={onWriting}
      onClose={onClose}
      onClosed={onClosed}
    />
  );
}

/**
 * The periodicity of the reading of the accounts under its title and, to a session that may modify the
 * accounts, the command that opens its form; the answer of the server shown while it is newer than the
 * schedule read. The command waits, inactive and saying why, while a write is under way (#661).
 */
export function IdentitySyncScheduleSection({
  schedule,
  editable,
}: {
  readonly schedule: IdentitySyncSchedule;
  /** Whether the session may modify the accounts (`platformOffer`): the command is offered. */
  readonly editable: boolean;
}) {
  const t = useTranslations("admin.identitySync.schedule");
  const [answered, setAnswered] = useState<IdentitySyncSchedule>();
  // The version the form opened on, which it writes from: none while it is closed.
  const [opened, setOpened] = useState<Opened>();
  const openings = useRef(0);
  const [writing, setWriting] = useState(false);
  const [said, say] = useSaid();
  const trigger = useRef<HTMLButtonElement>(null);
  const why = useId();
  const shown =
    answered !== undefined && answered.lock_version > schedule.lock_version ? answered : schedule;
  return (
    <Reactivations reads={[]}>
      <section aria-label={t("title")} className="space-y-2">
        <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
          <h3 className="flex items-center gap-2 font-medium">
            <CalendarClock aria-hidden="true" className="size-4" />
            {t("title")}
          </h3>
          {editable ? (
            <>
              <Button
                ref={trigger}
                type="button"
                variant="outline"
                size="sm"
                aria-disabled={writing ? true : undefined}
                aria-busy={writing}
                aria-describedby={writing ? why : undefined}
                className={UNAVAILABLE}
                onClick={() => {
                  if (writing) {
                    return;
                  }
                  openings.current += 1;
                  setOpened({ schedule: shown, at: new Date(), opening: openings.current });
                }}
              >
                {t("modify")}
              </Button>
              <WritingNote id={why} writing={writing} />
            </>
          ) : null}
        </div>
        <p role="status" aria-live="polite" className="text-muted-foreground empty:sr-only">
          {said === undefined ? null : <span key={said.count}>{said.text}</span>}
        </p>
        <IdentitySyncScheduleFacts schedule={shown} />
      </section>
      {opened === undefined || !editable ? null : (
        <ScheduleForm
          key={opened.opening}
          opened={opened}
          onDone={(answer) => {
            setAnswered((before) =>
              before === undefined || before.lock_version < answer.lock_version ? answer : before,
            );
            say(t("saved"));
            setOpened((current) => (current?.opening === opened.opening ? undefined : current));
          }}
          onWriting={setWriting}
          onClose={() => {
            setOpened(undefined);
          }}
          onClosed={() => trigger.current?.focus()}
        />
      )}
    </Reactivations>
  );
}
