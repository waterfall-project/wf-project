// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The schedule, the retention and the external copy of the backups (FBS-1.4, WF-ADM-0170,
 * EP-14/L43d): what the server reads of them, and, to a session that may modify the backups
 * (`backups.write`, WF-ADM-0100), their form, in the dialog of the forms of the reference data
 * (`ReferenceForm`).
 *
 * The form writes the schedule whole (`setBackupSchedule` is a `PUT`), from the version it opened on:
 * on or suspended, how often, on which day, at what time, how many backups are kept; and the copy of
 * each scheduled backup to an external location — one of those the installation declares
 * (`listExternalBackupLocations`), never a secret nor an address —, a folder relative to it, and as
 * many copies at least as the platform keeps backups (WF-EXP-0050), checked here before anything is
 * asked; « no copy » withdraws it. The time is entered in universal time, as the contract gives it,
 * and the local time it stands for today is said beside it — never converted here, a change of summer
 * time making a time of day without its date ambiguous. « Test the location » asks the server to
 * write then erase a witness file there (`testExternalBackupLocation`), and says its outcome.
 *
 * The answer takes the place of what the screen shows as long as it is newer than the schedule read
 * (`lock_version`) — against the fake back, which keeps nothing, for as long as the screen stays
 * (`MockupNotice`) —, and the page is read anew. A refusal by field is said at its field — a location
 * the installation does not declare, a path that is not relative, too few copies —, any other under
 * the form, the version stale (412) with the offer to read the page anew; a refusal answered once the
 * dialog is gone is told above the facts (`Reactivations`).
 */
"use client";

import { CalendarClock, FlaskConical, Pencil } from "lucide-react";
import { useTranslations } from "next-intl";
import { useRef, useState, useTransition } from "react";

import { setBackupSchedule, testExternalBackupLocation } from "@/api/actions/backups";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { rejected } from "@/components/commands/rejection";
import { useLocalTimestamp } from "@/components/local-time";
import { Reactivations } from "@/components/reference/reactivation";
import { type Draft, type FormField, ReferenceForm } from "@/components/reference/reference-form";
import { ReferenceSection } from "@/components/reference/section";
import { Button } from "@/components/ui/button";
import { localTimeOfDay } from "@/i18n/format";

type Schemas = components["schemas"];
type BackupSchedule = Schemas["BackupSchedule"];
type ExternalBackupLocation = Schemas["ExternalBackupLocation"];
type ExternalBackupLocationTest = Schemas["ExternalBackupLocationTest"];
type FieldProblem = Schemas["FieldProblem"];
type Frequency = NonNullable<BackupSchedule["frequency"]>;

/**
 * Every frequency of the contract, in the order of its enumeration: one the contract adds fails the
 * type check until it is here.
 */
const EVERY_FREQUENCY: Readonly<Record<Frequency, number>> = { daily: 0, weekly: 1 };

/** The frequencies a schedule may have, in the order of the contract. */
const FREQUENCIES = Object.keys(EVERY_FREQUENCY) as readonly Frequency[];

/** The days of a weekly schedule, from 1, Monday, as the contract numbers them (ISO 8601). */
const WEEKDAYS = [
  "monday",
  "tuesday",
  "wednesday",
  "thursday",
  "friday",
  "saturday",
  "sunday",
] as const;

/** The fields of the form, by the pointer of the contract each writes, without its first slash. */
const ENABLED = "is_enabled";
const FREQUENCY = "frequency";
const WEEKDAY = "weekday";
const AT = "at_time";
const RETAINED = "retained_count";
const LOCATION = "external_copy/location";
const PATH = "external_copy/path";
const COPIES = "external_copy/retained_count";
const COPYING = "external_copy/is_enabled";

/** The longest path the contract takes. */
const PATH_LENGTH = 255;

/**
 * The schedule of the backups — off, or how often, on which day, at what time —, their retention,
 * and the copy of each scheduled backup to an external location (WF-ADM-0170): none, or the location
 * the installation declares, the folder in it and the copies kept there, suspended or not. Its time
 * is said in universal time as the contract gives it.
 */
export function BackupScheduleFacts({ schedule }: { readonly schedule: BackupSchedule }) {
  const t = useTranslations("admin.schedule");
  const frequencies = useTranslations("enums.BackupSchedule.frequency");
  const weekday =
    schedule.frequency === "weekly" ? WEEKDAYS[(schedule.weekday ?? 0) - 1] : undefined;
  const facts: (readonly [string, string])[] = [
    [t("state"), schedule.is_enabled ? t("enabled") : t("disabled")],
  ];
  if (schedule.is_enabled) {
    if (schedule.frequency !== undefined) {
      facts.push([t("frequency"), frequencies(schedule.frequency)]);
    }
    if (weekday !== undefined) {
      facts.push([t("weekday"), t(`weekdays.${weekday}`)]);
    }
    if (schedule.at_time !== undefined) {
      facts.push([t("at"), t("universalTime", { time: schedule.at_time })]);
    }
  }
  facts.push([t("retained"), t("count", { count: schedule.retained_count })]);
  const copy = schedule.external_copy;
  if (copy === undefined) {
    facts.push([t("externalCopy"), t("externalCopyNone")]);
  } else {
    const named = { location: copy.location, path: copy.path, count: copy.retained_count };
    facts.push([
      t("externalCopy"),
      copy.is_enabled ? t("externalCopyTo", named) : t("externalCopySuspended", named),
    ]);
  }
  return (
    <dl className="grid w-fit grid-cols-[auto_auto] gap-x-6 gap-y-1 text-sm">
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
function draftOf(schedule: BackupSchedule): Draft {
  const copy = schedule.external_copy;
  return {
    [ENABLED]: String(schedule.is_enabled),
    [FREQUENCY]: schedule.frequency ?? "",
    [WEEKDAY]: schedule.weekday == null ? "" : String(schedule.weekday),
    [AT]: schedule.at_time ?? "",
    [RETAINED]: String(schedule.retained_count),
    [LOCATION]: copy?.location ?? "",
    [PATH]: copy?.path ?? "",
    [COPIES]: copy === undefined ? "" : String(copy.retained_count),
    [COPYING]: String(copy?.is_enabled ?? true),
  };
}

/** The frequency a value of the form names, as the contract writes it; none for any other. */
function frequencyOf(value: string | undefined): Frequency | undefined {
  return FREQUENCIES.find((frequency) => frequency === value);
}

/**
 * The schedule the form writes, whole, from the values checked and the version it opened on: the day
 * of a weekly schedule alone — none otherwise —, the frequency and the time when they are chosen —
 * a suspended schedule may leave them —, and no copy when no location is chosen, which withdraws the
 * copy set.
 */
function scheduleOf(values: Draft, lockVersion: number): BackupSchedule {
  const frequency = frequencyOf(values[FREQUENCY]);
  const at = values[AT] ?? "";
  const location = values[LOCATION] ?? "";
  return {
    is_enabled: values[ENABLED] === "true",
    ...(frequency === undefined ? {} : { frequency }),
    ...(at === "" ? {} : { at_time: at }),
    weekday: frequency === "weekly" ? Number(values[WEEKDAY]) : null,
    retained_count: Number(values[RETAINED]),
    ...(location === ""
      ? {}
      : {
          external_copy: {
            is_enabled: values[COPYING] === "true",
            location,
            path: values[PATH] ?? "",
            retained_count: Number(values[COPIES]),
          },
        }),
    lock_version: lockVersion,
  };
}

/** A field left empty that a rule requires. */
function requiredAt(field: string): FieldProblem {
  return { pointer: `/${field}`, code: "VALUE_REQUIRED" };
}

/**
 * The rules that bind the fields of the schedule, once each is checked, said at the field that
 * breaks each as the server would point at it: a schedule on names its frequency and its time — a
 * suspended one may leave them —, a weekly one its day; a copy, once a location is chosen, goes to a
 * location the installation declares (`locations`), names its folder and keeps as many copies at
 * least as the platform keeps backups (WF-EXP-0050), the least named. The bounds of a count are the
 * server's to judge.
 */
function scheduleRules(
  values: Draft,
  locations: readonly ExternalBackupLocation[],
): ReadonlyMap<string, FieldProblem> {
  const refused = new Map<string, FieldProblem>();
  if (values[ENABLED] === "true" && values[FREQUENCY] === "") {
    refused.set(FREQUENCY, requiredAt(FREQUENCY));
  }
  if (values[ENABLED] === "true" && values[AT] === "") {
    refused.set(AT, requiredAt(AT));
  }
  if (values[FREQUENCY] === "weekly" && values[WEEKDAY] === "") {
    refused.set(WEEKDAY, requiredAt(WEEKDAY));
  }
  const location = values[LOCATION] ?? "";
  if (location === "") {
    return refused;
  }
  if (!locations.some(({ name }) => name === location)) {
    refused.set(LOCATION, {
      pointer: `/${LOCATION}`,
      code: "UNKNOWN_EXTERNAL_BACKUP_LOCATION",
      params: { location },
    });
  }
  if (values[PATH] === "") {
    refused.set(PATH, requiredAt(PATH));
  }
  const copies = values[COPIES] ?? "";
  const retained = Number(values[RETAINED]);
  if (copies === "") {
    refused.set(COPIES, requiredAt(COPIES));
  } else if (Number(copies) < retained) {
    refused.set(COPIES, {
      pointer: `/${COPIES}`,
      code: "VALUE_OUT_OF_RANGE",
      params: { minimum: retained },
    });
  }
  return refused;
}

/** The outcome of a test of a location, its instant in the local time of the workstation. */
function TestOutcome({ test }: { readonly test: ExternalBackupLocationTest }) {
  const t = useTranslations("admin.schedule.form");
  const failures = useTranslations("enums.ExternalBackupFailure");
  const at = useLocalTimestamp(test.tested_at);
  const where = {
    location: test.location,
    at,
    folder: test.path == null ? "root" : "path",
    path: test.path ?? "",
  };
  return (
    <>
      {test.failure == null
        ? t("tested", where)
        : t("testFailed", { ...where, failure: failures(test.failure) })}
    </>
  );
}

/**
 * The outcome of a test as it is told: a folder the server refuses (422, `/path`) by the sentence of
 * its own code — the folder is what is wrong, not the request as a whole —, any other as it is.
 */
function toldOf(outcome: Outcome<ExternalBackupLocationTest>): Outcome<ExternalBackupLocationTest> {
  const folder =
    "problem" in outcome
      ? outcome.problem.fields?.find(({ pointer }) => pointer === "/path")
      : undefined;
  if (!("problem" in outcome) || folder === undefined) {
    return outcome;
  }
  const { correlation_id: correlation } = outcome.problem;
  return {
    ...outcome,
    problem: {
      code: folder.code,
      status: outcome.problem.status,
      params: folder.params ?? {},
      ...(correlation === undefined ? {} : { correlation_id: correlation }),
    },
  };
}

/** What the test of a location answered last, the folder it was asked for, and the how-many-th. */
interface Tested {
  readonly outcome: Outcome<ExternalBackupLocationTest>;
  readonly folder: string;
  readonly count: number;
}

/**
 * « Test the location » chosen, in the folder typed — at its root when none is —, and its outcome,
 * said in a region a reader of the screen hears; a refusal of the server — a folder that is not
 * relative (422), a location the installation does not declare (404) — said under it, the folder by
 * the sentence of its own code. Only the answer of the last test asked is said: one answered after
 * another was asked is left to fall; and it is said only while the folder typed is the one it tested —
 * the form keys the test by its location, which another location chosen starts anew.
 */
function LocationTest({ location, path }: { readonly location: string; readonly path: string }) {
  const t = useTranslations("admin.schedule.form");
  const [tested, setTested] = useState<Tested>();
  const [pending, startTransition] = useTransition();
  const asked = useRef(0);
  const test = () => {
    asked.current += 1;
    const count = asked.current;
    const folder = path.trim();
    startTransition(async () => {
      const outcome = await testExternalBackupLocation(
        location,
        folder === "" ? undefined : folder,
      ).catch(rejected);
      if (count === asked.current) {
        setTested({ outcome: toldOf(outcome), folder, count });
      }
    });
  };
  // What the folder typed now was tested for: nothing once it changed.
  const current = tested?.folder === path.trim() ? tested : undefined;
  const done = current?.outcome.kind === "done" ? current.outcome.data : undefined;
  return (
    <div className="grid justify-items-start gap-1">
      <Button type="button" variant="outline" size="sm" aria-busy={pending} onClick={test}>
        <FlaskConical aria-hidden="true" />
        {t(pending ? "testing" : "test")}
      </Button>
      <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
        {done === undefined || current === undefined ? null : (
          <span key={current.count}>
            <TestOutcome test={done} />
          </span>
        )}
      </p>
      <OutcomeNotice
        outcome={current?.outcome}
        onClear={() => {
          setTested(undefined);
        }}
      />
    </div>
  );
}

/**
 * The form of the schedule, opened on a version of it, at an instant that dates its local time, and
 * the how-many-th opening it is.
 */
interface Opened {
  readonly schedule: BackupSchedule;
  readonly at: Date;
  readonly opening: number;
}

/**
 * The first day from the one given, by the universal calendar, that falls on a day of the week
 * numbered as the contract does (1, Monday, to 7, Sunday): where a weekly time is taken this week.
 */
function nextWeekday(from: Date, weekday: number): Date {
  const today = from.getUTCDay() === 0 ? 7 : from.getUTCDay();
  return new Date(from.getTime() + ((weekday - today + 7) % 7) * 86_400_000);
}

/**
 * The form that sets the schedule whole, from the version it opened on: its fields, those of the copy
 * when the installation declares a location or the schedule sets a copy, and the test of the location
 * chosen.
 */
function ScheduleForm({
  opened: { schedule, at },
  locations,
  onDone,
  onClose,
  onClosed,
}: {
  readonly opened: Opened;
  readonly locations: readonly ExternalBackupLocation[];
  readonly onDone: (answer: BackupSchedule) => void;
  readonly onClose: () => void;
  readonly onClosed: () => void;
}) {
  const t = useTranslations("admin.schedule");
  const frequencies = useTranslations("enums.BackupSchedule.frequency");
  const kinds = useTranslations("enums.ExternalBackupLocationKind");
  const set = schedule.external_copy?.location;
  // A copy set to a location the installation no longer declares stays offered, by its name, rather
  // than withdrawn unsaid: the form refuses it at its field before anything is asked.
  const undeclared = set === undefined || locations.some(({ name }) => name === set) ? [] : [set];
  const copying = locations.length > 0 || undeclared.length > 0;
  /**
   * The local time a time typed stands for, said beside it: the time alone for a daily schedule; for
   * a weekly one, the local day too, which may be the one before or after the universal day. Each is
   * taken in the week the form is opened in, whose offset summer time may change; nothing for no time.
   */
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
      choices: FREQUENCIES.map((frequency) => [frequency, frequencies(frequency)] as const),
    },
    {
      name: WEEKDAY,
      label: t("weekday"),
      control: "choice",
      none: t("form.noWeekday"),
      choices: WEEKDAYS.map((day, index) => [String(index + 1), t(`weekdays.${day}`)] as const),
      note: t("form.weekdayNote"),
    },
    {
      name: AT,
      label: t("form.at"),
      control: "time",
      note: localTime,
      invalid: t("form.atInvalid"),
    },
    {
      name: RETAINED,
      label: t("form.retained"),
      control: "whole",
      required: true,
      invalid: t("form.retainedInvalid"),
    },
  ];
  if (copying) {
    fields.push(
      {
        name: LOCATION,
        label: t("form.location"),
        control: "choice",
        none: t("form.noCopy"),
        choices: [
          ...locations.map(
            ({ name, kind }) =>
              [name, t("form.locationChoice", { name, kind: kinds(kind) })] as const,
          ),
          ...undeclared.map((name) => [name, t("form.undeclared", { name })] as const),
        ],
        // What the installation says of the location chosen, as its configuration writes it.
        note: (draft) =>
          locations.find(({ name }) => name === draft[LOCATION])?.description ?? undefined,
      },
      {
        name: PATH,
        label: t("form.path"),
        control: "text",
        maxLength: PATH_LENGTH,
        note: t("form.pathNote"),
      },
      {
        name: COPIES,
        label: t("form.copies"),
        control: "whole",
        note: t("form.copiesNote"),
        invalid: t("form.copiesInvalid"),
      },
      {
        name: COPYING,
        label: t("form.copying"),
        control: "choice",
        required: true,
        choices: [
          ["true", t("form.copyOn")],
          ["false", t("form.copySuspended")],
        ],
      },
    );
  }
  return (
    <ReferenceForm<BackupSchedule>
      kind="backup_schedule"
      title={t("form.modify")}
      hint={t("form.hint")}
      creating={false}
      fields={fields}
      initial={draftOf(schedule)}
      rules={(values) => scheduleRules(values, locations)}
      // A location the installation declares alone is tested: the server would not find another.
      after={(draft) => {
        const chosen = locations.find(({ name }) => name === draft[LOCATION]);
        return chosen === undefined ? null : (
          <LocationTest key={chosen.name} location={chosen.name} path={draft[PATH] ?? ""} />
        );
      }}
      ask={(values) => setBackupSchedule(scheduleOf(values, schedule.lock_version))}
      target="set backup_schedule"
      answering={(answer) => answer}
      onDone={onDone}
      onClose={onClose}
      onClosed={onClosed}
    />
  );
}

/** What the last modification did, and the how-many-th it was. */
interface Said {
  readonly text: string;
  readonly count: number;
}

/**
 * The schedule of the backups under its title, and, to a session that may modify the backups — the
 * page hands over the locations the installation declares to it alone —, the command that opens its
 * form; the answer of the server shown while it is newer than the schedule read.
 */
export function BackupScheduleSection({
  schedule,
  locations,
}: {
  readonly schedule: BackupSchedule;
  /** The external locations the installation declares; none to a session that may not modify. */
  readonly locations: readonly ExternalBackupLocation[] | undefined;
}) {
  const t = useTranslations("admin.schedule");
  const [answered, setAnswered] = useState<BackupSchedule>();
  // The version the form opened on, which it writes from, and the how-many-th opening it is: none
  // while it is closed. An answer closes only the opening it was sent from, never one opened since.
  const [opened, setOpened] = useState<Opened>();
  const openings = useRef(0);
  const [said, setSaid] = useState<Said>();
  const trigger = useRef<HTMLButtonElement>(null);
  const shown =
    answered !== undefined && answered.lock_version > schedule.lock_version ? answered : schedule;
  const commands =
    locations === undefined ? undefined : (
      <div className="flex flex-wrap items-center gap-2">
        <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
          {said === undefined ? null : <span key={said.count}>{said.text}</span>}
        </p>
        <Button
          ref={trigger}
          type="button"
          variant="outline"
          size="sm"
          onClick={() => {
            openings.current += 1;
            setOpened({ schedule: shown, at: new Date(), opening: openings.current });
          }}
        >
          <Pencil aria-hidden="true" />
          {t("form.modify")}
        </Button>
      </div>
    );
  return (
    <Reactivations reads={[]}>
      <ReferenceSection title={t("title")} icon={CalendarClock} commands={commands}>
        <BackupScheduleFacts schedule={shown} />
      </ReferenceSection>
      {opened === undefined || locations === undefined ? null : (
        <ScheduleForm
          key={opened.opening}
          opened={opened}
          locations={locations}
          onDone={(answer) => {
            setAnswered((before) =>
              before === undefined || before.lock_version < answer.lock_version ? answer : before,
            );
            setSaid((before) => ({ text: t("form.saved"), count: (before?.count ?? 0) + 1 }));
            setOpened((current) => (current?.opening === opened.opening ? undefined : current));
          }}
          onClose={() => {
            setOpened(undefined);
          }}
          onClosed={() => trigger.current?.focus()}
        />
      )}
    </Reactivations>
  );
}
