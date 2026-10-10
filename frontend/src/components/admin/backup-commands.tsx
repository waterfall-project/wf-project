// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the backups (FBS-1.4, EP-02/L43c, EP-14/L42h): start one, under the permission of
 * the catalogue that guards it (`backups.write`, WF-ADM-0100); and, on each backup, those it lists
 * (`available_commands`, WF-IHM-0090) — mark it to be kept or no longer, whichever changes its
 * marking; download it; restore the platform from it —, each absent when the backup does not list
 * it, available, or unavailable with the conditions it lacks, as the server says them: a backup not
 * yet verified neither downloads nor restores, nothing restores while a backup runs, and nothing but
 * a download goes while a restoration runs. The front deduces none of it from the session nor from
 * the state of the backup. None deletes a backup. The rules are the guide's: « Les écrans de
 * l'administration ».
 *
 * A command the server lists unavailable stays presented, marked `aria-disabled` and described by
 * the conditions it lacks, as the activations of the reference data are (`UnavailableCellCommand`):
 * a press does not run it, and says in the region of the list what it lacks. The refusal of a
 * command the server opposes all the same — a state that forbids it (409), the condition named — is
 * told above the list as any other (`useListReport`).
 *
 * A backup has no counter: a marking answered shows the backup as the server answered it while each
 * reading anew of the page reads it as the one before did (`BackupCommands`) — against the fake back,
 * which keeps nothing, for as long as the screen stays.
 */
"use client";

import { Archive, ArchiveRestore, DatabaseBackup, Download, History } from "lucide-react";
import { usePathname, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import {
  createContext,
  type MouseEvent,
  type ReactNode,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";

import { retainBackup, startBackup } from "@/api/actions/backups";
import { type CommandOffer, findOffer } from "@/components/commands/offer";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { rejected } from "@/components/commands/rejection";
import { useLocalTimestamp } from "@/components/local-time";
import { CellCommand, UnavailableCellCommand } from "@/components/reference/cell-command";
import {
  ANOTHER_OBJECT,
  focusBack,
  type Said,
  WrittenRegion,
} from "@/components/reference/commands";
import { useListReport } from "@/components/reference/reactivation";
import type { ResultRefusal } from "@/components/tasks/result-refusal";
import { afterReveal, useTrackTask } from "@/components/tasks/task-tracker";
import { Button, buttonVariants } from "@/components/ui/button";
import { cn } from "@/components/ui/utils";
import { formatTimestamp } from "@/i18n/format";

import { type Backup, downloadHref, withoutDownloadRefusal } from "./backup-address";
import { RestoreDialog } from "./restore-dialog";

/** A command a backup lists, as the contract names it. */
type BackupCommand = Backup["available_commands"][number]["command"];

/** The answers to the markings, by backup, and the reading of the page they lie over. */
interface Held {
  readonly reading: readonly Backup[];
  readonly answers: ReadonlyMap<string, Backup>;
}

/** The restoration open, and the command that opened it, which the focus goes back to. */
interface Opened {
  readonly backup: Backup;
  readonly trigger: HTMLElement;
}

/** The commands of the list: the backups as shown, what the last one did, the restoration open. */
interface Commands {
  readonly shown: readonly Backup[];
  readonly answer: (answer: Backup) => void;
  readonly said: Said | undefined;
  readonly say: (text: string) => void;
  readonly opened: Opened | undefined;
  readonly open: (opened: Opened | undefined) => void;
}

/** The commands of the list of the backups; none outside it. */
const ListCommands = createContext<Commands | undefined>(undefined);

/**
 * The answers kept over a reading anew: those of the backups it reads as the reading before did; a
 * backup it reads otherwise, or no longer, lets its answer go, for good.
 */
function reread(held: Held, reading: readonly Backup[]): Held {
  const before = new Map(held.reading.map((backup) => [backup.backup_id, backup.is_retained]));
  const now = new Map(reading.map((backup) => [backup.backup_id, backup.is_retained]));
  const answers = new Map(
    [...held.answers].filter(([id]) => now.has(id) && now.get(id) === before.get(id)),
  );
  return { reading, answers };
}

/**
 * The commands of the list of the backups. The answers follow each reading of the page as it
 * arrives: the state is adjusted while rendering when the backups read change — the pattern React
 * admits for a state derived from a prop that changes (défaut n° 22 de `typescript.md`).
 */
export function BackupCommands({
  backups,
  children,
}: {
  /** The backups of the page, as the server read them. */
  readonly backups: readonly Backup[];
  readonly children: ReactNode;
}) {
  const [held, setHeld] = useState<Held>(() => ({ reading: backups, answers: new Map() }));
  const [said, setSaid] = useState<Said>();
  const [opened, open] = useState<Opened>();
  let current = held;
  if (held.reading !== backups) {
    current = reread(held, backups);
    setHeld(current);
  }
  const { reading, answers } = current;
  const commands = useMemo<Commands>(
    () => ({
      shown:
        answers.size === 0
          ? reading
          : reading.map((backup) => answers.get(backup.backup_id) ?? backup),
      answer: (answer) => {
        setHeld((before) => ({
          reading: before.reading,
          answers: new Map(before.answers).set(answer.backup_id, answer),
        }));
      },
      said,
      say: (text) => {
        setSaid((before) => ({ text, count: (before?.count ?? 0) + 1 }));
      },
      opened,
      open,
    }),
    [reading, answers, said, opened],
  );
  return <ListCommands value={commands}>{children}</ListCommands>;
}

/** The backups of a page as the list shows them, its markings answered; as read outside a list. */
export function useShownBackups(backups: readonly Backup[]): readonly Backup[] {
  return useContext(ListCommands)?.shown ?? backups;
}

/** The command that starts a backup now: the task goes to the tracker with it, to run it again. */
function StartBackupButton() {
  const t = useTranslations("admin.backups");
  const commands = useContext(ListCommands);
  const list = useListReport();
  const track = useTrackTask();
  const [pending, startTransition] = useTransition();
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      aria-busy={pending}
      onClick={() => {
        if (pending) {
          return;
        }
        const reading = list?.reading ?? "";
        startTransition(async () => {
          const outcome = await startBackup().catch(rejected);
          if (outcome.kind === "done") {
            track(outcome.data, { command: startBackup });
            commands?.say(t("started"));
          } else {
            list?.report({ outcome, reading, names: {}, target: "start" });
          }
        });
      }}
    >
      <DatabaseBackup aria-hidden="true" />
      {t("start")}
    </Button>
  );
}

/**
 * The head of the list, for a session that exercises a command: the region that says what the last
 * one did, and, for who may modify the backups, the command that starts one — on an empty list too.
 */
export function BackupHead({ startable }: { readonly startable: boolean }) {
  const said = useContext(ListCommands)?.said;
  return (
    <div className="flex flex-wrap items-center gap-2">
      <WrittenRegion said={said} />
      {startable ? <StartBackupButton /> : null}
    </div>
  );
}

/**
 * A command of a backup the server lists unavailable, with the conditions it lacks
 * (`UnavailableCellCommand`): pressed, it says them in the region of the list, after the command
 * named by the date of the backup.
 */
function UnavailableCommand({
  name,
  offer,
  children,
}: {
  /** The accessible name of the command, which names the backup by its date. */
  readonly name: string;
  readonly offer: CommandOffer;
  readonly children: ReactNode;
}) {
  const t = useTranslations("admin.backups");
  const commands = useContext(ListCommands);
  return (
    <UnavailableCellCommand
      name={name}
      offer={offer}
      onPress={(unmet) => {
        commands?.say(t("unavailable", { command: name, unmet }));
      }}
    >
      {children}
    </UnavailableCellCommand>
  );
}

/** The offer a backup lists of a command; none when it does not list it. */
function offerOf(backup: Backup, command: BackupCommand) {
  return findOffer(backup.available_commands, command);
}

/**
 * Whether a backup is marked to be kept, by a mark and a word, and the command that changes its
 * marking as the backup lists it — to keep, or no longer —, named after its date: absent, available,
 * or unavailable with the condition it lacks, while a restoration runs.
 */
export function RetentionCell({ backup }: { readonly backup: Backup }) {
  const t = useTranslations("admin.backups");
  const locale = useLocale();
  const commands = useContext(ListCommands);
  const list = useListReport();
  const date = useLocalTimestamp(backup.taken_at);
  const [pending, startTransition] = useTransition();
  const retained = backup.is_retained;
  const offer = offerOf(backup, retained ? "release" : "retain");
  const icon = retained ? <ArchiveRestore aria-hidden="true" /> : <Archive aria-hidden="true" />;
  const name = t(retained ? "releaseNamed" : "retainNamed", { date });
  const retain = () => {
    if (pending) {
      return;
    }
    const reading = list?.reading ?? "";
    startTransition(async () => {
      const answer = await retainBackup(backup.backup_id, !retained).catch(rejected);
      const outcome =
        answer.kind === "done" && answer.data.backup_id !== backup.backup_id
          ? ANOTHER_OBJECT
          : answer;
      if (outcome.kind === "done") {
        commands?.answer(outcome.data);
        commands?.say(
          t(outcome.data.is_retained ? "retainedSaid" : "releasedSaid", {
            date: formatTimestamp(backup.taken_at, locale),
          }),
        );
      } else {
        list?.report({ outcome, reading, names: {}, target: `retain ${backup.backup_id}` });
      }
    });
  };
  return (
    <span className="inline-flex items-center gap-1.5">
      {retained ? (
        <span className="inline-flex items-center gap-1.5">
          <Archive aria-hidden="true" className="size-4" />
          {t("retained")}
        </span>
      ) : null}
      {offer === undefined ? null : offer.is_available ? (
        <CellCommand aria-label={name} aria-busy={pending} onClick={retain}>
          {icon}
          {t(retained ? "release" : "retain")}
        </CellCommand>
      ) : (
        <UnavailableCommand name={name} offer={offer}>
          {icon}
          {t(retained ? "release" : "retain")}
        </UnavailableCommand>
      )}
    </span>
  );
}

/**
 * The download of a backup, as it lists it: a link to the route that hands it on as a stream,
 * leaving from the screen as it shows, without a refusal it came back with — Enter on its cell
 * follows it —; unavailable, with the condition it lacks, until the backup is verified.
 */
export function DownloadCell({ backup }: { readonly backup: Backup }) {
  const t = useTranslations("admin.backups");
  const pathname = usePathname();
  const search = useSearchParams().toString();
  const date = useLocalTimestamp(backup.taken_at);
  const offer = offerOf(backup, "download");
  if (offer === undefined) {
    return null;
  }
  const name = t("downloadNamed", { date });
  if (!offer.is_available) {
    return (
      <UnavailableCommand name={name} offer={offer}>
        <Download aria-hidden="true" />
        {t("download")}
      </UnavailableCommand>
    );
  }
  const from = withoutDownloadRefusal({ pathname, search: search === "" ? "" : `?${search}` });
  return (
    <a
      href={downloadHref(backup.backup_id, from)}
      tabIndex={-1}
      aria-label={name}
      className={cn(buttonVariants({ variant: "outline", size: "sm" }), "h-5 px-1.5 text-xs")}
    >
      <Download aria-hidden="true" />
      {t("download")}
    </a>
  );
}

/**
 * The command that opens the restoration of the platform from a backup, named after its date, as
 * the backup lists it: unavailable, with the conditions it lacks, until it is verified and while a
 * backup or a restoration runs.
 */
export function RestoreCell({ backup }: { readonly backup: Backup }) {
  const t = useTranslations("admin.backups");
  const commands = useContext(ListCommands);
  const date = useLocalTimestamp(backup.taken_at);
  const offer = offerOf(backup, "restore");
  if (offer === undefined) {
    return null;
  }
  const name = t("restoreNamed", { date });
  if (!offer.is_available) {
    return (
      <UnavailableCommand name={name} offer={offer}>
        <History aria-hidden="true" />
        {t("restore")}
      </UnavailableCommand>
    );
  }
  return (
    <CellCommand
      aria-label={name}
      onClick={(event: MouseEvent<HTMLElement>) => {
        commands?.open({ backup, trigger: event.currentTarget });
      }}
    >
      <History aria-hidden="true" />
      {t("restore")}
    </CellCommand>
  );
}

/**
 * The restoration open, within the list, on the backup as the page shows it now — the one read anew
 * after a date refused (`BACKUP_DATE_MISMATCH`), so that the dialog states and sends the date read,
 * never again the one captured at the press; the one of the press when the page no longer holds it.
 * Closed, it gives the focus back to the cell of its command, or to the list when the page read anew
 * no longer holds it (`focusBack`).
 */
export function RestoreOpened() {
  const commands = useContext(ListCommands);
  const list = useListReport();
  const opened = commands?.opened;
  if (commands === undefined || opened === undefined) {
    return null;
  }
  const shown = commands.shown.find((backup) => backup.backup_id === opened.backup.backup_id);
  return (
    <RestoreDialog
      backup={shown ?? opened.backup}
      onStarted={commands.say}
      onClose={() => {
        commands.open(undefined);
      }}
      onClosed={() => {
        focusBack(opened, list?.refocus);
      }}
    />
  );
}

/** What the refusal of a download is about: the backup by its date, once the browser has written it. */
function RefusedDownload({ backup }: { readonly backup: Backup }) {
  const t = useTranslations("admin.backups");
  const date = useLocalTimestamp(backup.taken_at);
  return date === "" ? t("downloadRefused") : t("downloadRefusedNamed", { date });
}

/**
 * The refusal of a download the route sent the browser back with, told above the list until
 * dismissed — kept from the first rendering, whatever the address says next —, the backup named by
 * its date when the page holds it. Rendered by the server, it is in the document before a reader of
 * the screen could hear it: it takes the focus once mounted, as a bound refused does. The address no
 * longer carries it once the page is revealed, so that a reload does not tell it again
 * (`afterReveal`) — dismissed early or not.
 */
export function DownloadRefusal({
  refused,
}: {
  readonly refused: { readonly id: string; readonly refusal: ResultRefusal } | undefined;
}) {
  const t = useTranslations("admin.backups");
  const list = useListReport();
  const backup = useContext(ListCommands)?.shown.find((each) => each.backup_id === refused?.id);
  const [told, setTold] = useState(refused?.refusal);
  const [carried] = useState(refused !== undefined);
  const region = useRef<HTMLDivElement>(null);
  const lead = useId();
  useEffect(() => {
    if (!carried) {
      return undefined;
    }
    region.current?.focus();
    return afterReveal(() => {
      window.history.replaceState(
        window.history.state,
        "",
        withoutDownloadRefusal(window.location),
      );
    });
  }, [carried]);
  if (told === undefined) {
    return null;
  }
  return (
    <div
      ref={region}
      role="group"
      aria-labelledby={lead}
      tabIndex={-1}
      className="space-y-1 rounded-md outline-none focus-visible:ring-2 focus-visible:ring-ring"
    >
      <p id={lead} className="text-sm font-medium text-destructive">
        {backup === undefined ? t("downloadRefused") : <RefusedDownload backup={backup} />}
      </p>
      <OutcomeNotice
        outcome={told}
        onClear={() => {
          setTold(undefined);
        }}
        onDismissed={list?.refocus}
        dismissible
      />
    </div>
  );
}
