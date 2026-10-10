// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The restoration of the platform from a backup of the list (WF-ADM-0160, EP-02/L43c), confirmed in
 * a dialog that states the date of the backup, its verification, what is lost and that the
 * restoration is recorded in the journal of audit (WF-SEC-0030); it restores only once the
 * identifier of the backup is typed — a backup has no label —, whatever its case. While the request
 * is on its way, the dialog stays: neither Escape, a click outside nor « Annuler » closes it, so that
 * a refusal is told in it and nothing restores that the user believes abandoned — a state that
 * forbids the restoration (409), the condition named, as any outcome; a date confirmed that is not
 * that of the backup named (422, `BACKUP_DATE_MISMATCH` on `/acknowledged_backup_taken_at`,
 * EP-14/L42h) at the date the dialog states, which the list gave: the list read is no longer that of
 * the backup, and the page reads anew. The task goes to the tracker without its command: a
 * restoration starts again from this confirmation alone.
 */
"use client";

import { History, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { type SubmitEvent, useId, useState, useTransition } from "react";

import { startRestore } from "@/api/actions/backups";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { rejected } from "@/components/commands/rejection";
import { useTrackTask } from "@/components/tasks/task-tracker";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { formatTimestamp } from "@/i18n/format";
import { problemMessage } from "@/i18n/problem";

type Backup = components["schemas"]["Backup"];
type FieldProblem = components["schemas"]["FieldProblem"];

/** The pointer of the contract to the date the confirmation states (`RestoreRequest`). */
const DATE_POINTER = "/acknowledged_backup_taken_at";

/**
 * A refusal as the dialog tells it: the refusal of the date stated, said at the date; the rest —
 * the envelope with its other fields, if any — told as any outcome.
 */
function placed(answer: Outcome<unknown>): {
  readonly date: FieldProblem | undefined;
  readonly told: Outcome<unknown> | undefined;
} {
  if (!("problem" in answer) || answer.problem.fields === undefined) {
    return { date: undefined, told: answer };
  }
  const date = answer.problem.fields.find((field) => field.pointer === DATE_POINTER);
  const rest = answer.problem.fields.filter((field) => field !== date);
  if (date === undefined) {
    return { date, told: answer };
  }
  return {
    date,
    told:
      rest.length === 0 ? undefined : { ...answer, problem: { ...answer.problem, fields: rest } },
  };
}

/**
 * Confirm the restoration of the platform from a backup, by its identifier typed, then restore and
 * hand the task over to the tracker.
 */
export function RestoreDialog({
  backup,
  onStarted,
  onClose,
  onClosed,
}: {
  readonly backup: Backup;
  /** Say that the restoration started, in the region of the list. */
  readonly onStarted: (text: string) => void;
  readonly onClose: () => void;
  /** Give the focus back where the dialog was opened from, once it has closed. */
  readonly onClosed: () => void;
}) {
  const t = useTranslations("admin.restore");
  const locale = useLocale();
  const messages = useMessages();
  const router = useRouter();
  const track = useTrackTask();
  const id = useId();
  const [typed, setTyped] = useState("");
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [dateRefused, setDateRefused] = useState<FieldProblem>();
  const [pending, startTransition] = useTransition();
  // Shown in the browser alone, which knows its time zone: the dialog opens on a press.
  const date = formatTimestamp(backup.taken_at, locale);
  const confirmed = typed.trim().toLowerCase() === backup.backup_id.toLowerCase();

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending || !confirmed) {
      return;
    }
    setOutcome(undefined);
    setDateRefused(undefined);
    startTransition(async () => {
      const answer = await startRestore(backup.backup_id, backup.taken_at).catch(rejected);
      if (answer.kind === "done") {
        track(answer.data, { subject: date });
        onStarted(t("started", { date }));
        onClose();
        return;
      }
      const refusal = placed(answer);
      setDateRefused(refusal.date);
      setOutcome(refusal.told);
      if (refusal.date !== undefined) {
        // The date stated is the list's: the list is no longer that of the backup, and reads anew.
        router.refresh();
      }
    });
  };

  return (
    <Dialog
      open
      onOpenChange={(opened) => {
        // Nothing closes the dialog while the request is on its way.
        if (!opened && !pending) {
          onClose();
        }
      }}
    >
      <DialogContent
        aria-busy={pending}
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          onClosed();
        }}
      >
        <DialogHeader>
          <DialogTitle>{t("title")}</DialogTitle>
          <DialogDescription>
            {t("warning", { date, verification: backup.verification })}
          </DialogDescription>
          {dateRefused === undefined ? null : (
            <p role="alert" className="text-sm font-medium text-destructive">
              {problemMessage(dateRefused, { locale, messages })}
            </p>
          )}
        </DialogHeader>
        <form aria-label={t("title")} noValidate onSubmit={submit} className="grid gap-3">
          <div className="grid gap-1">
            <Label htmlFor={`${id}-typed`}>{t("confirm")}</Label>
            <p id={`${id}-identifier`} className="text-sm">
              {t.rich("identifier", {
                code: () => <code className="font-mono select-all">{backup.backup_id}</code>,
              })}
            </p>
            <Input
              id={`${id}-typed`}
              value={typed}
              autoComplete="off"
              spellCheck={false}
              aria-describedby={`${id}-identifier`}
              onChange={(change) => {
                setTyped(change.target.value);
              }}
            />
          </div>
          <OutcomeNotice
            outcome={outcome}
            onClear={() => {
              setOutcome(undefined);
            }}
            onDismissed={onClose}
          />
          <DialogFooter>
            <Button type="button" variant="outline" disabled={pending} onClick={onClose}>
              <X aria-hidden="true" />
              {t("cancel")}
            </Button>
            <Button type="submit" disabled={!confirmed} aria-busy={pending}>
              <History aria-hidden="true" />
              {t(pending ? "sending" : "submit")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
