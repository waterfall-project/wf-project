// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The state of the platform and its backups (FBS-1.3, FBS-1.4, US-0250), as the server gives them,
 * in its order. The state (WF-ADM-0130): each component, whether it is available and when it was
 * last checked; the storage used and available; the last reading of the accounts of the identity
 * provider, the last backup and the last restoration test, each dated with its outcome and the
 * motive of a failure; the alerts under way, each with its zone, by `Signal`, and what it names —
 * the component unavailable, the storage used and free (WF-OBS-0030). The backups
 * (WF-ADM-0150): a page of their list on the dense grid, sorted and filtered by the server as the
 * address asks (WF-IHM-0130, EP-14/L42h) — by period, origin, verification, marking and size —,
 * with the commands each backup lists (`available_commands`, WF-IHM-0090) — mark it to be kept or
 * no longer, download it, restore the platform from it — and, for a session that may modify the
 * backups, the command that starts one (EP-02/L43c, `backup-commands.tsx`). Their schedule, their
 * retention and its form are `backup-schedule.tsx` (EP-14/L43d).
 */
import {
  Bell,
  CircleCheck,
  CircleX,
  DatabaseBackup,
  HardDrive,
  History,
  Server,
} from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import type { ReactNode } from "react";

import type { components } from "@/api/generated/schema";
import type { Problem } from "@/api/problem";
import { ChoiceFilter } from "@/components/grid/choice-filter";
import { refusedBounds, refusedSides } from "@/components/grid/filters";
import { ListPages } from "@/components/grid/list-pages";
import { refusedPeriod } from "@/components/grid/period";
import { PeriodFilter } from "@/components/grid/period-filter";
import { type GridQuery, OFFSET } from "@/components/grid/query";
import { RangeFilter } from "@/components/grid/range-filter";
import type { GridPreferences } from "@/components/grid/settings";
import { ValuesFilter } from "@/components/grid/values-filter";
import { LocalTime } from "@/components/local-time";
import { CELL, ICON, ListTable } from "@/components/projects/project-tables";
import { Reactivations } from "@/components/reference/reactivation";
import { BoundsRefused, ReferenceSection } from "@/components/reference/section";
import { Signal } from "@/components/signal/signal";
import { TableCell, TableHead, TableRow } from "@/components/ui/table";
import type { ResultRefusal } from "@/components/tasks/result-refusal";
import { formatBytes } from "@/i18n/format";
import { problemMessage } from "@/i18n/problem";
import type { ListPage } from "@/navigation/pages";

import {
  type Backup,
  BACKUP_ORIGINS,
  BACKUP_VERIFICATIONS,
  type BackupFilters,
  type BackupSort,
  BACKUPS_LIST,
  BACKUPS_READS,
  IS_RETAINED,
  narrows,
  ORIGINS,
  SIZE_BYTES,
  VERIFICATIONS,
} from "./backup-address";
import { BackupCommands, BackupHead, DownloadRefusal, RestoreOpened } from "./backup-commands";
import { BackupGrid } from "./backup-grid";

type SystemStatus = components["schemas"]["SystemStatus"];
type ComponentHealth = components["schemas"]["ComponentHealth"];
type OperationOutcome = components["schemas"]["OperationOutcome"];
type Alert = components["schemas"]["Alert"];

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
        <OperationRow name={t("directorySync")} outcome={status.last_directory_sync} />
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

/** A page of the backups, as the contract gives it; or the envelope of the filters the API refused. */
export type BackupsRead =
  | { readonly kind: "read"; readonly items: readonly Backup[]; readonly page: ListPage }
  | { readonly kind: "refused"; readonly problem: Problem };

/**
 * The filters of the backups (WF-IHM-0130): the period they were taken in, two local days drawn as
 * instants; their origins and their verifications, a button for each value of the contract; their
 * marking, one choice; the bounds of their size in bytes. Each only changes the address, back to the
 * first page. A bound the API refused (422) — an end before the start, a size at most below the
 * least — is said at its field.
 */
function BackupFilterBar({
  filters,
  refused,
}: {
  readonly filters: BackupFilters;
  /** The envelope of the filters the API refused; none when it read the list. */
  readonly refused: Problem | undefined;
}) {
  const t = useTranslations();
  const origins = useTranslations("enums.BackupOrigin");
  const verifications = useTranslations("enums.BackupVerification");
  const fields = refused?.fields ?? [];
  return (
    <div className="flex flex-wrap items-start gap-x-6 gap-y-2">
      <PeriodFilter
        label={t("admin.backups.period")}
        kind="day"
        period={filters.period}
        refused={refusedPeriod(fields)}
        page={OFFSET}
      />
      <ValuesFilter
        name={ORIGINS}
        label={t("admin.backups.originFilter")}
        every={t("admin.backups.everyOrigin")}
        values={BACKUP_ORIGINS.map((origin) => ({ value: origin, text: origins(origin) }))}
        chosen={filters.origins}
        page={OFFSET}
      />
      <ValuesFilter
        name={VERIFICATIONS}
        label={t("admin.backups.verificationFilter")}
        every={t("admin.backups.everyVerification")}
        values={BACKUP_VERIFICATIONS.map((outcome) => ({
          value: outcome,
          text: verifications(outcome),
        }))}
        chosen={filters.verifications}
        page={OFFSET}
      />
      <ChoiceFilter
        name={IS_RETAINED}
        label={t("admin.backups.retentionFilter")}
        every={t("admin.backups.everyRetention")}
        choices={[
          { value: "true", text: t("admin.backups.retainedOnes") },
          { value: "false", text: t("admin.backups.rotatingOnes") },
        ]}
        chosen={filters.retained === undefined ? undefined : String(filters.retained)}
        page={OFFSET}
      />
      <RangeFilter
        label={t("admin.backups.bounds")}
        kind="bytes"
        columns={[
          {
            column: SIZE_BYTES,
            label: t("admin.backups.sizeBytes"),
            bounds: filters.size,
            refused: refusedSides(refusedBounds(fields), SIZE_BYTES),
          },
        ]}
        page={OFFSET}
      />
    </div>
  );
}

/**
 * The backups of a page of the list, on the dense grid (`BackupGrid`), filtered and sorted as the
 * address asks, or that there is none — only when the list holds none at all and nothing narrows
 * it: a page asked beyond its end shows no grid, and its pages say where it stands (`ListPages`);
 * filters the API refused (422) leave the list unread, the bound said at its field, a sentence
 * standing for the grid — that of the period when the API refused it, that of the bounds otherwise. The head of the list says what the last command did, and offers to start a
 * backup to who may modify them (`startable`); the refusals, and that of a download the browser came
 * back with, are told above the list. The commands of each backup are those it lists.
 */
export function BackupList({
  read,
  filters,
  query,
  preferences,
  startable,
  refused,
}: {
  readonly read: BackupsRead;
  readonly filters: BackupFilters;
  readonly query: GridQuery<BackupSort>;
  readonly preferences: GridPreferences | undefined;
  /** Whether the session may start a backup (`backups.write`, `platformOffer`). */
  readonly startable: boolean;
  /** The download refused the browser came back with, if any. */
  readonly refused: { readonly id: string; readonly refusal: ResultRefusal } | undefined;
}) {
  const t = useTranslations("admin.backups");
  const backups = read.kind === "read" ? read.items : [];
  const listed = backups.some((backup) => backup.available_commands.length > 0);
  const empty = read.kind === "read" && read.page.total === 0 && !narrows(filters);
  let body: ReactNode;
  if (read.kind === "refused" && refusedPeriod(read.problem.fields ?? []) !== undefined) {
    body = <p className="text-sm text-destructive">{t("periodRefused")}</p>;
  } else if (read.kind === "refused") {
    body = <BoundsRefused />;
  } else if (read.items.length === 0) {
    body = (
      <p className="text-sm text-muted-foreground">{t("count", { count: read.page.total })}</p>
    );
  } else {
    body = (
      <BackupGrid backups={read.items} page={read.page} query={query} preferences={preferences} />
    );
  }
  return (
    <BackupCommands backups={backups}>
      <Reactivations reads={BACKUPS_READS}>
        <DownloadRefusal refused={refused} />
        <ReferenceSection
          title={t("title")}
          icon={DatabaseBackup}
          empty={empty ? t("none") : undefined}
          commands={startable || listed ? <BackupHead startable={startable} /> : undefined}
          fill
        >
          <BackupFilterBar
            filters={filters}
            refused={read.kind === "refused" ? read.problem : undefined}
          />
          {body}
          {read.kind === "read" ? (
            <ListPages
              list={BACKUPS_LIST}
              texts="admin.pages"
              page={read.page}
              shown={read.items.length}
            />
          ) : null}
        </ReferenceSection>
        <RestoreOpened />
      </Reactivations>
    </BackupCommands>
  );
}
