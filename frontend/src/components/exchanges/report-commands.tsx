// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The second step of an import (WF-ARC-0100, WF-INTF-0080), from its report: its application,
 * never without the confirmation the page asks first — then one operation, a background task the
 * tracker of the shell follows (WF-ARC-0090) —; or its abandonment, which leaves the project
 * unchanged and leads back to the screen as it was before the import. Each is offered as the
 * import of its kind is (WF-IHM-0090), and only while the status of the import allows it; a
 * refusal of the server is told under the command (`OutcomeNotice`).
 */
"use client";

import { Ban, CheckCheck, FileCheck, X } from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState, useTransition } from "react";

import { abandonFileImport, applyFileImport } from "@/api/actions/exchanges";
import type { Outcome } from "@/api/problem";
import { Command } from "@/components/commands/command";
import { commandIcon } from "@/components/commands/icons";
import type { CommandOffer } from "@/components/commands/offer";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { useTrackTask } from "@/components/tasks/task-tracker";
import { Button } from "@/components/ui/button";

import { shownImport } from "./offers";

/** The import a report is of, what the server offers of it, and where the screen started. */
export interface ReportCommandsProps {
  readonly projectId: string;
  readonly importId: string;
  /** The file of the import, which names the task of its application. */
  readonly filename: string;
  /** The import of its kind, as the server offers it; `undefined` where it is not offered. */
  readonly offer: CommandOffer | undefined;
  /** What the status of the import still allows. */
  readonly steps: { readonly apply: boolean; readonly abandon: boolean };
  /** The address of the screen, its context kept, before any import was shown. */
  readonly start: string;
}

/** The confirmation of the application, asked in the page before anything is applied. */
function ConfirmForm({
  id,
  projectId,
  importId,
  filename,
  onClose,
}: Pick<ReportCommandsProps, "projectId" | "importId" | "filename"> & {
  readonly id: string;
  readonly onClose: () => void;
}) {
  const t = useTranslations("exchanges.report");
  const track = useTrackTask();
  const confirm = useRef<HTMLButtonElement>(null);
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  useEffect(() => {
    confirm.current?.focus();
  }, []);
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    const command = () => applyFileImport(projectId, importId);
    startTransition(async () => {
      const result = await command();
      if (result.kind === "done") {
        track(result.data, { command, subject: filename });
        onClose();
      } else {
        setOutcome(result);
      }
    });
  };
  return (
    <form
      id={id}
      aria-label={t("confirmTitle")}
      aria-busy={pending}
      onSubmit={submit}
      className="space-y-2 rounded-md border p-3 text-sm"
    >
      <p>{t("confirmQuestion", { file: filename })}</p>
      <div className="flex gap-2">
        <Button type="submit" size="sm" ref={confirm}>
          <CheckCheck aria-hidden="true" />
          {t("confirm")}
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          <X aria-hidden="true" />
          {t("cancel")}
        </Button>
      </div>
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
    </form>
  );
}

/** Offer to apply the import, once confirmed, and to abandon it. */
export function ReportCommands({
  projectId,
  importId,
  filename,
  offer,
  steps,
  start,
}: ReportCommandsProps) {
  const t = useTranslations("exchanges.report");
  const router = useRouter();
  const form = useId();
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const close = () => {
    setOpen(false);
    button.current?.focus();
  };
  // The screen goes back to where it started only if it still shows this import: the user may
  // have opened another one, or left, while the abandonment was asked.
  const abandon = async () => {
    const outcome = await abandonFileImport(projectId, importId);
    if (outcome.kind === "done" && shownImport() === importId) {
      router.push(start);
    }
    return outcome;
  };
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-start gap-2">
        <Command
          offer={steps.apply ? offer : undefined}
          label={t("apply")}
          icon={commandIcon(FileCheck)}
          disclosure={{
            expanded: open,
            controls: form,
            toggle: () => {
              setOpen(!open);
            },
            ref: button,
          }}
        />
        <Command
          offer={steps.abandon ? offer : undefined}
          label={t("abandon")}
          icon={commandIcon(Ban)}
          action={abandon}
        />
      </div>
      {open ? (
        <ConfirmForm
          id={form}
          projectId={projectId}
          importId={importId}
          filename={filename}
          onClose={close}
        />
      ) : null}
    </div>
  );
}
