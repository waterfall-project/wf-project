// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the backups (FBS-1.4, EP-02/L43c, EP-14/L42h, US-0440): start one, under the
 * permission of the catalogue that guards it (`backups.write`, WF-ADM-0100); deposit a backup copied
 * out of another installation, in the parts the server cuts it into (#350), then restore the
 * platform from it, under the permission of the restoration (`platform_restore`) — the deposit is
 * no command of a backup of the list, which none lists —; and, on each backup, those it lists
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
 * which keeps nothing, for as long as the screen stays. A restoration, from a backup of the list or
 * from a deposit, is confirmed in the one dialog (`RestoreDialog`), then followed by the screen of
 * its maintenance (`Restoration`).
 */
"use client";

import { Archive, ArchiveRestore, DatabaseBackup, Download, History, Upload } from "lucide-react";
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

import {
  completeBackupDeposit,
  type FileUpload,
  openBackupDeposit,
  retainBackup,
  sendBackupPart,
  startBackup,
} from "@/api/actions/backups";
import type { Outcome } from "@/api/problem";
import { useHeldCommand } from "@/components/commands/held";
import { type CommandOffer, findOffer } from "@/components/commands/offer";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { LocalTime, useLocalTimestamp } from "@/components/local-time";
import { useNoteMessage } from "@/components/notices/message-history";
import { type Said, type Say, useSaid } from "@/components/notices/said";
import { CellCommand, UnavailableCellCommand } from "@/components/reference/cell-command";
import { ANOTHER_OBJECT, focusBack, WrittenRegion } from "@/components/reference/commands";
import { useListReport } from "@/components/reference/reactivation";
import type { ResultRefusal } from "@/components/tasks/result-refusal";
import { afterReveal, useTrackTask } from "@/components/tasks/task-tracker";
import { Button, buttonVariants } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/components/ui/utils";
import { formatTimestamp } from "@/i18n/format";

import { type Backup, downloadHref, withoutDownloadRefusal } from "./backup-address";
import { RestoreDialog, type RestoreSubject } from "./restore-dialog";

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
  readonly say: Say;
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
  const [said, say] = useSaid();
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
      say,
      opened,
      open,
    }),
    [reading, answers, said, say, opened],
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
  const own = useHeldCommand();
  const held = list?.held ?? own;
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
        const generation = list?.generation ?? 0;
        startTransition(async () => {
          const outcome = await held(startBackup());
          if (outcome.kind === "done") {
            track(outcome.data, { command: startBackup });
          }
          // In the transition too, which an update after an await is not by itself: the list tells
          // the answer in the commit that ends the request, never while the press is held (#1484).
          startTransition(() => {
            if (outcome.kind === "done") {
              // The tracker notes the task handed over: the history has it once.
              commands?.say(t("started"), { noted: false });
            } else {
              list?.report({ outcome, generation, names: {}, target: "start" });
            }
          });
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
  help,
  offer,
  children,
}: {
  /** The accessible name of the command, which names the backup by its date. */
  readonly name: string;
  /** What the command does, translated. */
  readonly help: string;
  readonly offer: CommandOffer;
  readonly children: ReactNode;
}) {
  const t = useTranslations("admin.backups");
  const commands = useContext(ListCommands);
  return (
    <UnavailableCellCommand
      name={name}
      help={help}
      offer={offer}
      onPress={(unmet) => {
        commands?.say(t("unavailable", { command: name, unmet }), { noted: false });
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
  const said = useTranslations("commands");
  const locale = useLocale();
  const commands = useContext(ListCommands);
  const list = useListReport();
  const date = useLocalTimestamp(backup.taken_at);
  const own = useHeldCommand();
  const held = list?.held ?? own;
  const [pending, startTransition] = useTransition();
  const retained = backup.is_retained;
  const offer = offerOf(backup, retained ? "release" : "retain");
  const icon = retained ? <ArchiveRestore aria-hidden="true" /> : <Archive aria-hidden="true" />;
  const name = t(retained ? "releaseNamed" : "retainNamed", { date });
  const help = said(retained ? "releaseBackup.help" : "retainBackup.help");
  const retain = () => {
    if (pending) {
      return;
    }
    const generation = list?.generation ?? 0;
    startTransition(async () => {
      const answer = await held(retainBackup(backup.backup_id, !retained));
      const outcome =
        answer.kind === "done" && answer.data.backup_id !== backup.backup_id
          ? ANOTHER_OBJECT
          : answer;
      // In the transition too, which an update after an await is not by itself: the list tells the
      // answer in the commit that ends the request, never while the press is held (#1484).
      startTransition(() => {
        if (outcome.kind === "done") {
          commands?.answer(outcome.data);
          commands?.say(
            t(outcome.data.is_retained ? "retainedSaid" : "releasedSaid", {
              date: formatTimestamp(backup.taken_at, locale),
            }),
            { object: formatTimestamp(backup.taken_at, locale) },
          );
        } else {
          list?.report({ outcome, generation, names: {}, target: `retain ${backup.backup_id}` });
        }
      });
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
        <CellCommand label={name} help={help} aria-busy={pending} onClick={retain}>
          {icon}
          {t(retained ? "release" : "retain")}
        </CellCommand>
      ) : (
        <UnavailableCommand name={name} help={help} offer={offer}>
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
  const said = useTranslations("commands");
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
      <UnavailableCommand name={name} help={said("downloadBackup.help")} offer={offer}>
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
  const said = useTranslations("commands");
  const commands = useContext(ListCommands);
  const date = useLocalTimestamp(backup.taken_at);
  const offer = offerOf(backup, "restore");
  if (offer === undefined) {
    return null;
  }
  const name = t("restoreNamed", { date });
  if (!offer.is_available) {
    return (
      <UnavailableCommand name={name} help={said("restoreBackup.help")} offer={offer}>
        <History aria-hidden="true" />
        {t("restore")}
      </UnavailableCommand>
    );
  }
  return (
    <CellCommand
      label={name}
      help={said("restoreBackup.help")}
      onClick={(event: MouseEvent<HTMLElement>) => {
        commands?.open({ backup, trigger: event.currentTarget });
      }}
    >
      <History aria-hidden="true" />
      {t("restore")}
    </CellCommand>
  );
}

/** What the confirmation of the restoration from a backup of the list states and sends. */
function listed(backup: Backup): RestoreSubject {
  return {
    source: { backup_id: backup.backup_id },
    takenAt: backup.taken_at,
    identifier: backup.backup_id,
    verification: backup.verification,
  };
}

/**
 * The restoration open, within the list, on the backup as the page shows it now — the one read anew
 * after a date refused (`CONFIRMATION_REQUIRED`), so that the dialog states and sends the date read,
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
      subject={listed(shown ?? opened.backup)}
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

/** How far a deposit has come: the part being sent, of how many. */
interface Sending {
  readonly part: number;
  readonly count: number;
}

/**
 * Deposit an archive, part after part, as the server cut it: the parts it says received are not
 * sent again. The first refusal stops the deposit.
 */
async function deposit(
  file: File,
  held: ReturnType<typeof useHeldCommand>,
  progress: (sending: Sending) => void,
): Promise<Outcome<FileUpload>> {
  const opened = await held(openBackupDeposit(file.name, file.size));
  if (opened.kind !== "done") {
    return opened;
  }
  const { chunked_upload_id: id, part_count: count, part_size_bytes: size } = opened.data;
  const received = new Set(opened.data.received_parts);
  for (let part = 1; part <= count; part += 1) {
    if (!received.has(part)) {
      progress({ part, count });
      const form = new FormData();
      form.set("part", file.slice((part - 1) * size, part * size));
      const sent = await held(sendBackupPart(id, part, form));
      if (sent.kind !== "done") {
        return sent;
      }
    }
  }
  return held(completeBackupDeposit(id));
}

/**
 * What the confirmation of the restoration from a deposit states and sends: the date its manifest
 * says, and the identifier of the deposit to type; its verification to come, by its restoration
 * (EP-14/L42o). None for the file of an import, which dates no backup.
 */
function deposited(upload: FileUpload): RestoreSubject | undefined {
  const takenAt = upload.backup_taken_at;
  return takenAt === null
    ? undefined
    : {
        source: { external_backup_upload_id: upload.upload_id },
        takenAt,
        identifier: upload.upload_id,
        verification: "pending",
      };
}

/**
 * The deposit of a backup copied out of another installation, then the restoration of the platform
 * from it, at the date its manifest says, confirmed as that of a backup of the list
 * (`RestoreDialog`) — the whole platform replaced (WF-ADM-0160). Closed, the confirmation gives the
 * focus back to the command that opened it.
 */
export function BackupDeposit() {
  const t = useTranslations("admin.deposit");
  const locale = useLocale();
  const held = useHeldCommand();
  const field = useId();
  const restore = useRef<HTMLButtonElement>(null);
  const [file, setFile] = useState<File>();
  const [sending, setSending] = useState<Sending>();
  const [upload, setUpload] = useState<FileUpload>();
  const [confirming, setConfirming] = useState(false);
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const send = () => {
    if (pending || file === undefined) {
      return;
    }
    setUpload(undefined);
    setOutcome(undefined);
    startTransition(async () => {
      const result = await deposit(file, held, setSending);
      // In the transition too, which an update after an await is not by itself — the progress
      // alone is told while the deposit runs: its end is told in the commit that ends the request,
      // never while the choice of a file is held (#1484).
      startTransition(() => {
        setSending(undefined);
        if (result.kind === "done") {
          setUpload(result.data);
        } else {
          setOutcome(result);
        }
      });
    });
  };
  const subject = upload === undefined ? undefined : deposited(upload);
  // The deposit done, noted in the history of the messages: the date in the time of the workstation.
  useNoteMessage(
    upload,
    upload === undefined || subject === undefined
      ? undefined
      : {
          tone: "success",
          sentence: t.markup("deposited", {
            name: upload.filename,
            time: () => formatTimestamp(subject.takenAt, locale),
          }),
          object: upload.filename,
        },
  );
  return (
    <section aria-label={t("title")} className="shrink-0 space-y-2 text-sm">
      <h2 className="text-base font-semibold">{t("title")}</h2>
      <p className="text-muted-foreground">{t("explanation")}</p>
      <div className="flex flex-wrap items-end gap-2">
        <div className="space-y-1">
          <Label htmlFor={field}>{t("file")}</Label>
          <Input
            id={field}
            type="file"
            disabled={pending}
            onChange={(event) => {
              setFile(event.target.files?.[0]);
              setUpload(undefined);
            }}
          />
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          aria-busy={pending}
          disabled={file === undefined}
          onClick={send}
        >
          <Upload aria-hidden="true" />
          {t("send")}
        </Button>
      </div>
      {sending === undefined ? null : <p role="status">{t("sending", { ...sending })}</p>}
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
      {upload === undefined || subject === undefined ? null : (
        <div className="flex flex-wrap items-center gap-2">
          <p role="status">
            {t.rich("deposited", {
              name: upload.filename,
              time: () => <LocalTime value={subject.takenAt} />,
            })}
          </p>
          <Button
            ref={restore}
            type="button"
            size="sm"
            variant="outline"
            onClick={() => {
              setConfirming(true);
            }}
          >
            <History aria-hidden="true" />
            {t("restore")}
          </Button>
        </div>
      )}
      {confirming && subject !== undefined ? (
        <RestoreDialog
          subject={subject}
          onClose={() => {
            setConfirming(false);
          }}
          onClosed={() => {
            restore.current?.focus();
          }}
        />
      ) : null}
    </section>
  );
}
