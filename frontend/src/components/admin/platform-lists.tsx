// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The state of the platform and its backups (FBS-1.3, FBS-1.4, US-0250), as the server gives them,
 * in its order. The state (WF-ADM-0130): each component, whether it is available and when it was
 * last checked; the storage used and available; the last reading of the accounts of the identity
 * provider, the last backup and the last restoration test, each dated with its outcome and the
 * motive of a failure; the alerts under way, each with its zone, by `Signal`, and what it names —
 * the component unavailable, the storage used and free (WF-OBS-0030). The backups
 * (WF-ADM-0150): each with its date, its size, its verification, whether it was taken by hand or
 * on schedule, and whether it is marked to be kept; and their schedule and retention
 * (WF-ADM-0170), its time said in universal time as the contract gives it, unconverted: a time
 * of day has no date to take the offset of a zone with summer time from. Read only: neither a
 * backup nor a restoration is started here — the commands belong to the epic of the operation of
 * the platform.
 */
import {
  Archive,
  Bell,
  CalendarClock,
  CircleCheck,
  CircleX,
  DatabaseBackup,
  HardDrive,
  History,
  Server,
} from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";

import type { components } from "@/api/generated/schema";
import { LocalTime } from "@/components/local-time";
import { CELL, ICON, ListTable } from "@/components/projects/project-tables";
import { ReferenceSection } from "@/components/reference/section";
import { Signal } from "@/components/signal/signal";
import { TableCell, TableHead, TableRow } from "@/components/ui/table";
import { formatBytes } from "@/i18n/format";
import { problemMessage } from "@/i18n/problem";
import type { ListPage } from "@/navigation/pages";

type SystemStatus = components["schemas"]["SystemStatus"];
type ComponentHealth = components["schemas"]["ComponentHealth"];
type OperationOutcome = components["schemas"]["OperationOutcome"];
type Alert = components["schemas"]["Alert"];
type Backup = components["schemas"]["Backup"];
type BackupSchedule = components["schemas"]["BackupSchedule"];

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

/** Whether something holds — a component available, an operation succeeded —, by a mark and a word. */
function Outcome({
  ok,
  yes,
  no,
}: {
  readonly ok: boolean;
  readonly yes: string;
  readonly no: string;
}) {
  const Icon = ok ? CircleCheck : CircleX;
  return (
    <span className="inline-flex items-center gap-1.5">
      <Icon aria-hidden="true" className={ICON} />
      {ok ? yes : no}
    </span>
  );
}

/** The components of the platform, each available or not, when last checked, and its version. */
export function ComponentList({
  components: list,
}: {
  readonly components: readonly ComponentHealth[];
}) {
  const t = useTranslations("admin.status");
  const names = useTranslations("enums.PlatformComponent");
  return (
    <ReferenceSection title={t("components")} icon={Server}>
      <ListTable
        label={t("components")}
        columns={[t("component"), t("availability"), t("checkedAt"), t("componentVersion")]}
      >
        {list.map((health) => (
          <TableRow key={health.component}>
            <TableCell className={CELL}>{names(health.component)}</TableCell>
            <TableCell className={CELL}>
              <Outcome ok={health.is_available} yes={t("available")} no={t("unavailable")} />
            </TableCell>
            <TableCell className={CELL}>
              <LocalTime value={health.checked_at} />
            </TableCell>
            <TableCell className={`${CELL} tabular-nums`}>{health.version ?? null}</TableCell>
          </TableRow>
        ))}
      </ListTable>
    </ReferenceSection>
  );
}

/** The storage used and available, each in the unit it fills. */
export function StorageFacts({ storage }: { readonly storage: SystemStatus["storage"] }) {
  const t = useTranslations("admin.status");
  const locale = useLocale();
  const facts = [
    ["used", storage.used_bytes],
    ["free", storage.available_bytes],
  ] as const;
  return (
    <ReferenceSection title={t("storage")} icon={HardDrive}>
      <dl className="grid w-fit grid-cols-[auto_auto] gap-x-6 gap-y-1 text-sm">
        {facts.map(([key, value]) => (
          <div key={key} className="contents">
            <dt className="text-muted-foreground">{t(key)}</dt>
            <dd className="text-right tabular-nums">{formatBytes(value, locale)}</dd>
          </div>
        ))}
      </dl>
    </ReferenceSection>
  );
}

/** A last operation of the platform: when, its outcome, and the motive of a failure; or never. */
function OperationRow({
  name,
  outcome,
}: {
  readonly name: string;
  readonly outcome: OperationOutcome | null | undefined;
}) {
  const t = useTranslations("admin.status");
  const locale = useLocale();
  const messages = useMessages();
  return (
    <TableRow>
      <TableHead scope="row" className={`${CELL} font-normal`}>
        {name}
      </TableHead>
      {outcome == null ? (
        <TableCell className={`${CELL} text-muted-foreground`} colSpan={3}>
          {t("never")}
        </TableCell>
      ) : (
        <>
          <TableCell className={CELL}>
            <LocalTime value={outcome.at} />
          </TableCell>
          <TableCell className={CELL}>
            <Outcome ok={outcome.succeeded} yes={t("succeeded")} no={t("failed")} />
          </TableCell>
          <TableCell className={CELL}>
            {outcome.problem == null ? null : problemMessage(outcome.problem, { locale, messages })}
          </TableCell>
        </>
      )}
    </TableRow>
  );
}

/**
 * The last reading of the accounts of the identity provider, the last backup, its last copy
 * outside the platform (WF-EXP-0050) and the last restoration test.
 */
export function OperationList({ status }: { readonly status: SystemStatus }) {
  const t = useTranslations("admin.status");
  return (
    <ReferenceSection title={t("operations")} icon={History}>
      <ListTable
        label={t("operations")}
        columns={[t("operation"), t("at"), t("outcome"), t("motive")]}
      >
        <OperationRow name={t("identitySync")} outcome={status.last_identity_sync} />
        <OperationRow name={t("backup")} outcome={status.last_backup} />
        <OperationRow name={t("backupCopy")} outcome={status.last_backup_copy} />
        <OperationRow name={t("restoreTest")} outcome={status.last_restore_test} />
      </ListTable>
    </ReferenceSection>
  );
}

/**
 * What an alert names besides its code, as the server gives it: the component unavailable, the
 * storage used and free, the external location a copy of a backup did not reach and why; nothing
 * for an alert that names none.
 */
function AlertDetail({ alert }: { readonly alert: Alert }) {
  const t = useTranslations();
  const locale = useLocale();
  const {
    component,
    used_bytes: used,
    available_bytes: available,
    location,
    failure,
  } = alert.params ?? {};
  if (
    alert.code === "scheduled_backup_copy_failed" &&
    location !== undefined &&
    failure !== undefined
  ) {
    return (
      <span className="block text-muted-foreground">
        {t("admin.status.copyDetail", {
          location,
          failure: t(`enums.ExternalBackupFailure.${failure}`),
        })}
      </span>
    );
  }
  if (alert.code === "component_unavailable" && component !== undefined) {
    return (
      <span className="block text-muted-foreground">
        {t(`enums.PlatformComponent.${component}`)}
      </span>
    );
  }
  if (alert.code === "storage_nearly_full" && used !== undefined && available !== undefined) {
    return (
      <span className="block text-muted-foreground">
        {t("admin.status.storageDetail", {
          used: formatBytes(used, locale),
          available: formatBytes(available, locale),
        })}
      </span>
    );
  }
  return null;
}

/** The alerts under way, each with its zone, what it is about and since when. */
export function AlertList({ alerts }: { readonly alerts: readonly Alert[] }) {
  const t = useTranslations("admin.status");
  const codes = useTranslations("enums.Alert.code");
  return (
    <ReferenceSection
      title={t("alerts")}
      icon={Bell}
      empty={alerts.length === 0 ? t("noAlert") : undefined}
    >
      <ListTable label={t("alerts")} columns={[t("severity"), t("alert"), t("since")]}>
        {alerts.map((alert) => (
          <TableRow key={`${alert.code}-${alert.since}`}>
            <TableCell className={CELL}>
              <Signal zone={alert.severity} />
            </TableCell>
            <TableCell className={CELL}>
              {codes(alert.code)}
              <AlertDetail alert={alert} />
            </TableCell>
            <TableCell className={CELL}>
              <LocalTime value={alert.since} />
            </TableCell>
          </TableRow>
        ))}
      </ListTable>
    </ReferenceSection>
  );
}

/**
 * The backups of a page of the list, each dated, sized and verified; or that there is none — only
 * when the list holds none at all: a page asked beyond its end shows no table, and its pages say
 * where it stands (`ListPages`).
 */
export function BackupList({
  backups,
  page,
}: {
  readonly backups: readonly Backup[];
  readonly page: ListPage;
}) {
  const t = useTranslations("admin.backups");
  const enums = useTranslations("enums.Backup");
  const locale = useLocale();
  return (
    <ReferenceSection
      title={t("title")}
      icon={DatabaseBackup}
      empty={page.total === 0 ? t("none") : undefined}
    >
      {backups.length === 0 ? null : (
        <ListTable
          label={t("title")}
          columns={[t("takenAt"), t("size"), t("verification"), t("origin"), t("retention")]}
        >
          {backups.map((backup) => (
            <TableRow key={backup.backup_id}>
              <TableCell className={CELL}>
                <LocalTime value={backup.taken_at} />
              </TableCell>
              <TableCell className={`${CELL} text-right tabular-nums`}>
                {formatBytes(backup.size_bytes, locale)}
              </TableCell>
              <TableCell className={CELL}>{enums(`verification.${backup.verification}`)}</TableCell>
              <TableCell className={CELL}>
                {backup.origin === undefined ? null : enums(`origin.${backup.origin}`)}
              </TableCell>
              <TableCell className={CELL}>
                {backup.is_retained ? (
                  <span className="inline-flex items-center gap-1.5">
                    <Archive aria-hidden="true" className={ICON} />
                    {t("retained")}
                  </span>
                ) : null}
              </TableCell>
            </TableRow>
          ))}
        </ListTable>
      )}
    </ReferenceSection>
  );
}

/**
 * The schedule of the backups — off, or how often, on which day, at what time —, their retention,
 * and the copy of each scheduled backup to an external location (WF-ADM-0170): none, or the
 * location the installation declares, the folder in it and the copies kept there, suspended or
 * not. Read only: the form that sets them comes with the commands of the backups (#519).
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
    <ReferenceSection title={t("title")} icon={CalendarClock}>
      <dl className="grid w-fit grid-cols-[auto_auto] gap-x-6 gap-y-1 text-sm">
        {facts.map(([term, value]) => (
          <div key={term} className="contents">
            <dt className="text-muted-foreground">{term}</dt>
            <dd>{value}</dd>
          </div>
        ))}
      </dl>
    </ReferenceSection>
  );
}
