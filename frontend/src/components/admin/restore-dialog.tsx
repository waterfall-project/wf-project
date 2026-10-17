// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The restoration of the platform from a backup of the list (WF-ADM-0160, EP-02/L43c) or from a
 * deposit (US-0440, #350), confirmed in a dialog that states the date of the backup, its
 * verification — that of a deposit is to come, its restoration verifies it (EP-14/L42o) —, what is
 * lost, that the users are signed out and that the restoration is recorded in the journal of audit
 * (WF-SEC-0030); it restores only once the identifier of the backup or of the deposit is typed — a
 * backup has no label —, whatever its case. While the request is on its way, the dialog stays:
 * neither Escape, a click outside nor « Annuler » closes it, so that a refusal is told in it and
 * nothing restores that the user believes abandoned — a state that forbids the restoration (409),
 * the condition named, as any outcome; a date confirmed that is not that of the backup named (400,
 * `CONFIRMATION_REQUIRED`, EP-03/US-0440/L2) at the date the dialog states, which the list gave: the
 * list read is no longer that of the backup, and the page reads anew. Queued, the restoration is
 * handed over to the screen of its maintenance (`Restoration`), which follows it to its end: a
 * restoration starts again from this confirmation alone.
 */
"use client";

import { History, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { type SubmitEvent, useId, useState, useTransition } from "react";

import { type RestoreSource, startRestore } from "@/api/actions/backups";
import type { Outcome, Problem } from "@/api/problem";
import { useHeldCommand } from "@/components/commands/held";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
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

import type { BackupVerification } from "./backup-address";
import { useFollowRestoration } from "./restoration";

/** What a restoration replaces the platform with, as the dialog states and sends it. */
export interface RestoreSubject {
  readonly source: RestoreSource;
  /** The date of the backup, as the API gave it, which the dialog states and the request sends. */
  readonly takenAt: string;
  /** What the user types to confirm: the identifier of the backup, or of the deposit. */
  readonly identifier: string;
  /** How far the backup is verified: a deposit is verified by its restoration (`pending`). */
  readonly verification: BackupVerification;
}

/**
 * A refusal as the dialog tells it: a date confirmed that is not that of the backup (400,
 * `CONFIRMATION_REQUIRED`), said at the date; the rest told as any outcome.
 */
function placed(answer: Outcome<unknown>): {
  readonly date: Problem | undefined;
  readonly told: Outcome<unknown> | undefined;
} {
  if ("problem" in answer && answer.problem.code === "CONFIRMATION_REQUIRED") {
    return { date: answer.problem, told: undefined };
  }
  return { date: undefined, told: answer };
}

/**
 * Confirm the restoration of the platform from a backup or a deposit, by its identifier typed, then
 * restore and hand the task over to the screen of its maintenance.
 */
export function RestoreDialog({
  subject,
  onClose,
  onClosed,
}: {
  readonly subject: RestoreSubject;
  readonly onClose: () => void;
  /** Give the focus back where the dialog was opened from, once it has closed. */
  readonly onClosed: () => void;
}) {
  const t = useTranslations("admin.restore");
  const locale = useLocale();
  const messages = useMessages();
  const router = useRouter();
  const held = useHeldCommand();
  const follow = useFollowRestoration();
  const id = useId();
  const [typed, setTyped] = useState("");
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [dateRefused, setDateRefused] = useState<Problem>();
  const [pending, startTransition] = useTransition();
  // Shown in the browser alone, which knows its time zone: the dialog opens on a press.
  const date = formatTimestamp(subject.takenAt, locale);
  const confirmed = typed.trim().toLowerCase() === subject.identifier.toLowerCase();

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending || !confirmed) {
      return;
    }
    setOutcome(undefined);
    setDateRefused(undefined);
    startTransition(async () => {
      const answer = await held(startRestore(subject.source, subject.takenAt));
      if (answer.kind === "done") {
        onClose();
        follow(answer.data.task_id);
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
            {t("warning", { date, verification: subject.verification })}
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
                code: () => <code className="font-mono select-all">{subject.identifier}</code>,
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
