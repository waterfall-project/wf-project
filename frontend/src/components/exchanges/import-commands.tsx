// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The first step of an import (WF-ARC-0100): a command for each kind of file the server offers
 * to import (WF-IHM-0090), which opens, in the page, the choice of the file. Sent, the file is
 * deposited and its analysis opened by a server action, which gives the import back at once: the
 * task that analyses it goes to the tracker of the shell (WF-ARC-0090), and the screen shows the
 * report of the import — its analysis under way, until the tracker offers to read the screen anew.
 * Nothing is judged of the content of the file here: its format and its version are the
 * analysis' to check (WF-INTF-0070), and a refusal is told under the form (`OutcomeNotice`); its
 * size only, past the largest an import takes (§4.6.2), is refused at once. An extraction of
 * actual costs declares the period it covers, if the user gives it.
 */
"use client";

import {
  Calculator,
  CalendarRange,
  FileSearch,
  FileUp,
  Hourglass,
  type LucideIcon,
  X,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState, useTransition } from "react";

import { type ExchangeKind, openFileImport } from "@/api/actions/exchanges";
import type { Outcome } from "@/api/problem";
import { Command } from "@/components/commands/command";
import { commandIcon } from "@/components/commands/icons";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { useTrackTask } from "@/components/tasks/task-tracker";
import { Button } from "@/components/ui/button";

import {
  EXCHANGE_KINDS,
  IMPORT_MAX_BYTES,
  importHref,
  type ImportOffers,
  MEBIBYTE,
  shownScreen,
} from "./offers";

/** The field of a date. */
const DATE = "h-8 rounded-md border border-input bg-background px-2 text-foreground";

/** The icon of the import of each kind: that of the command which modifies the same content. */
const KIND_ICONS: Readonly<Record<ExchangeKind, LucideIcon>> = {
  ms_project_schedule: CalendarRange,
  estimate: Calculator,
  remaining: Hourglass,
  actual_costs: FileUp,
};

/** The imports the server offers, the project, and the address of the screen in its context. */
export interface ImportCommandsProps {
  readonly projectId: string;
  readonly offers: ImportOffers;
  /** The address of the screen, its context kept, from which the report of an import is shown. */
  readonly start: string;
}

/** The form of the file of an import: the kind chosen, and what closes the form. */
interface FileFormProps extends Omit<ImportCommandsProps, "offers"> {
  readonly id: string;
  readonly kind: ExchangeKind;
  readonly onClose: () => void;
}

/** The extraction of actual costs declares the period it covers (WF-INTF-0140, WF-CRE-0050). */
function PeriodFields({
  from,
  to,
  onFrom,
  onTo,
}: {
  readonly from: string;
  readonly to: string;
  readonly onFrom: (value: string) => void;
  readonly onTo: (value: string) => void;
}) {
  const t = useTranslations("exchanges.import");
  return (
    <fieldset className="flex flex-wrap gap-3">
      <legend className="mb-1 text-sm font-medium">{t("period")}</legend>
      <label className="flex items-center gap-2 text-sm">
        {t("periodFrom")}
        <input
          type="date"
          value={from}
          onChange={(event) => {
            onFrom(event.target.value);
          }}
          className={DATE}
        />
      </label>
      <label className="flex items-center gap-2 text-sm">
        {t("periodTo")}
        <input
          type="date"
          value={to}
          onChange={(event) => {
            onTo(event.target.value);
          }}
          className={DATE}
        />
      </label>
    </fieldset>
  );
}

/** What the form says of the file chosen: none, or one past the largest size an import takes. */
type FileProblem = "missing" | "tooLarge";

/** The API out of reach: the server action itself did not answer. */
const UNREACHABLE: Outcome<never> = { kind: "unreachable" };

/** Ask the file to import, deposit it, open its analysis, and show the report of the import. */
function FileForm({ id, kind, projectId, start, onClose }: FileFormProps) {
  const t = useTranslations("exchanges.import");
  const track = useTrackTask();
  const router = useRouter();
  const field = useId();
  const input = useRef<HTMLInputElement>(null);
  const [problem, setProblem] = useState<FileProblem>();
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  useEffect(() => {
    input.current?.focus();
  }, []);

  // The form is checked here, not by the browser: a file missing, or larger than an import
  // takes — which the server of Next would refuse before the API is asked —, is said in the page,
  // in the language of the interface, and the field keeps the focus.
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    const file = input.current?.files?.[0];
    if (file === undefined || file.size > IMPORT_MAX_BYTES) {
      setProblem(file === undefined ? "missing" : "tooLarge");
      input.current?.focus();
      return;
    }
    const form = new FormData();
    form.set("file", file);
    const asked =
      kind === "actual_costs"
        ? { kind, period_from: from === "" ? null : from, period_to: to === "" ? null : to }
        : { kind };
    startTransition(async () => {
      const result = await openFileImport(projectId, asked, form).catch(() => UNREACHABLE);
      if (result.kind !== "done") {
        setOutcome(result);
        return;
      }
      const opened = result.data;
      if (opened.task !== undefined) {
        track(opened.task, { subject: opened.filename });
      }
      // The report is shown only if the screen is still the one the file was sent from.
      if (shownScreen() === start.split("?")[0]) {
        router.push(importHref(start, opened.import_id));
      }
      onClose();
    });
  };

  return (
    <form
      id={id}
      aria-label={t(`kinds.${kind}`)}
      aria-busy={pending}
      noValidate
      onSubmit={submit}
      className="space-y-2 rounded-md border p-3"
    >
      <label htmlFor={field} className="block text-sm font-medium">
        {t("file")}
      </label>
      <input
        id={field}
        ref={input}
        type="file"
        required
        aria-invalid={problem === undefined ? undefined : true}
        aria-describedby={problem === undefined ? undefined : `${field}-problem`}
        onChange={() => {
          setProblem(undefined);
        }}
        className="block w-full max-w-sm text-sm"
      />
      {problem === undefined ? null : (
        <p id={`${field}-problem`} role="alert" className="text-sm text-destructive">
          {problem === "missing"
            ? t("fileRequired")
            : t("fileTooLarge", { max: IMPORT_MAX_BYTES / MEBIBYTE })}
        </p>
      )}
      {kind === "actual_costs" ? (
        <PeriodFields from={from} to={to} onFrom={setFrom} onTo={setTo} />
      ) : null}
      <div className="flex gap-2">
        <Button type="submit" size="sm">
          <FileSearch aria-hidden="true" />
          {t("analyse")}
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

/** Offer the import of each kind of file, and open the choice of its file when pressed. */
export function ImportCommands({ projectId, offers, start }: ImportCommandsProps) {
  const t = useTranslations("exchanges.import.kinds");
  const form = useId();
  const [open, setOpen] = useState<ExchangeKind>();
  const buttons = useRef<Partial<Record<ExchangeKind, HTMLButtonElement | null>>>({});
  const close = () => {
    setOpen(undefined);
    if (open !== undefined) {
      buttons.current[open]?.focus();
    }
  };
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-start gap-2">
        {EXCHANGE_KINDS.map((kind) => (
          <Command
            key={kind}
            offer={offers[kind]}
            label={t(kind)}
            icon={commandIcon(KIND_ICONS[kind])}
            disclosure={{
              expanded: open === kind,
              controls: form,
              toggle: () => {
                setOpen(open === kind ? undefined : kind);
              },
              ref: (button) => {
                buttons.current[kind] = button;
              },
            }}
          />
        ))}
      </div>
      {open === undefined ? null : (
        <FileForm
          key={open}
          id={form}
          kind={open}
          projectId={projectId}
          start={start}
          onClose={close}
        />
      )}
    </div>
  );
}
