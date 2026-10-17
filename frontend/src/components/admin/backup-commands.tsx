// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the screen of the backups (US-0440): a backup asked, which the worker takes and
 * the tracker of the shell follows to its end (WF-ADM-0150, WF-ARC-0090); the restoration of a
 * backup of the list (`Restoration`); the deposit of a backup copied out of another installation,
 * in the parts the server cuts it into (#350), then its restoration at the date its manifest says;
 * and the refusal of a download, which the route of the archive carries back in the address.
 * Every refusal of the API is told where its command is (`OutcomeNotice`).
 */
"use client";

import { ArchiveRestore, DatabaseBackup, Upload } from "lucide-react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { useId, useState, useTransition } from "react";

import {
  completeBackupDeposit,
  type FileUpload,
  openBackupDeposit,
  sendBackupPart,
  startPlatformBackup,
} from "@/api/actions/backups";
import type { Outcome } from "@/api/problem";
import { useHeldCommand } from "@/components/commands/held";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { LocalTime } from "@/components/local-time";
import { useTrackTask } from "@/components/tasks/task-tracker";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import { DOWNLOAD_REFUSAL } from "./backup-address";
import { useAskRestore } from "./restoration";

/** Ask a backup of the platform, and hand its task over to the tracker. */
export function StartBackup() {
  const t = useTranslations("admin.backups");
  const track = useTrackTask();
  const held = useHeldCommand();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const start = () => {
    if (pending) {
      return;
    }
    startTransition(async () => {
      const result = await held(startPlatformBackup());
      if (result.kind === "done") {
        setOutcome(undefined);
        track(result.data, { command: startPlatformBackup });
      } else {
        setOutcome(result);
      }
    });
  };
  return (
    <div className="space-y-2">
      <Button type="button" size="sm" aria-busy={pending} onClick={start}>
        <DatabaseBackup aria-hidden="true" />
        {t("start")}
      </Button>
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
    </div>
  );
}

/** Restore the platform from a backup of the list, once its date is confirmed. */
export function RestoreBackup({
  backupId,
  takenAt,
}: {
  readonly backupId: string;
  /** The date of the backup, as the API gave it, which the confirmation names. */
  readonly takenAt: string;
}) {
  const t = useTranslations("admin.backups");
  const ask = useAskRestore();
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      onClick={() => {
        ask({ source: { backup_id: backupId }, takenAt });
      }}
    >
      <ArchiveRestore aria-hidden="true" />
      {t("restore")}
    </Button>
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
 * The deposit of a backup copied out of another installation, then its restoration at the date its
 * manifest says — the whole platform replaced, as for a backup of the list (WF-ADM-0160).
 */
export function BackupDeposit() {
  const t = useTranslations("admin.deposit");
  const held = useHeldCommand();
  const ask = useAskRestore();
  const field = useId();
  const [file, setFile] = useState<File>();
  const [sending, setSending] = useState<Sending>();
  const [deposited, setDeposited] = useState<FileUpload>();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const send = () => {
    if (pending || file === undefined) {
      return;
    }
    setDeposited(undefined);
    setOutcome(undefined);
    startTransition(async () => {
      const result = await deposit(file, held, setSending);
      setSending(undefined);
      if (result.kind === "done") {
        setDeposited(result.data);
      } else {
        setOutcome(result);
      }
    });
  };
  const takenAt = deposited?.backup_taken_at;
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
              setDeposited(undefined);
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
      {deposited === undefined || takenAt === undefined ? null : (
        <div className="flex flex-wrap items-center gap-2">
          <p role="status">
            {t.rich("deposited", {
              name: deposited.filename,
              time: () => <LocalTime value={takenAt} />,
            })}
          </p>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => {
              ask({ source: { external_backup_upload_id: deposited.upload_id }, takenAt });
            }}
          >
            <ArchiveRestore aria-hidden="true" />
            {t("restore")}
          </Button>
        </div>
      )}
    </section>
  );
}

/**
 * The refusal of a download, which the route of the archive carried back in the address: told
 * until dismissed, which takes it away from the address.
 */
export function DownloadRefusal({ refusal }: { readonly refusal: Outcome<never> | undefined }) {
  const router = useRouter();
  const pathname = usePathname();
  const search = new URLSearchParams(useSearchParams());
  search.delete(DOWNLOAD_REFUSAL);
  const kept = search.toString();
  return (
    <OutcomeNotice
      outcome={refusal}
      dismissible
      onClear={() => {
        router.replace(kept === "" ? pathname : `${pathname}?${kept}`, { scroll: false });
      }}
    />
  );
}
