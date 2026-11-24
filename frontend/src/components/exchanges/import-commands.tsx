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

import { FileSearch, X } from "lucide-react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState } from "react";

import type { ExchangeKind } from "@/api/actions/exchanges";
import type { Outcome } from "@/api/problem";
import { Command } from "@/components/commands/command";
import { commandIcon, PROJECT_COMMAND_ICONS } from "@/components/commands/icons";
import { OutcomeNotice, useReadAnew } from "@/components/commands/outcome-notice";
import { WaitingIcon, waitingAttributes } from "@/components/commands/waiting";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

import {
  EXCHANGE_KINDS,
  IMPORT_COMMAND,
  IMPORT_MAX_BYTES,
  type ImportOffers,
  MEBIBYTE,
  type MappingGap,
} from "./offers";
import { useOpenImport } from "./open-import";

/** The field of a date, as wide as the date. */
const DATE = "w-auto";

/** The imports the server offers, the project, and the address of the screen in its context. */
export interface ImportCommandsProps {
  readonly projectId: string;
  readonly offers: ImportOffers;
  /** The address of the screen, its context kept, from which the report of an import is shown. */
  readonly start: string;
  /** What the correspondence of the extraction lacks, when the session may read it. */
  readonly gap?: MappingGap | undefined;
}

/** The form of the file of an import: the kind chosen, and what closes the form. */
interface FileFormProps extends Omit<ImportCommandsProps, "offers" | "gap"> {
  readonly id: string;
  readonly kind: ExchangeKind;
  /** Closes this opening of the form, and no other: the one that is open by then stays. */
  readonly onClose: () => void;
  /** Tells whether the file is being sent, from the press to the answer, whether open or not. */
  readonly onSending: (sending: boolean) => void;
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
        <Input
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
        <Input
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

/** Ask the file to import, deposit it, open its analysis, and show the report of the import. */
function FileForm({ id, kind, projectId, start, onClose, onSending }: FileFormProps) {
  const t = useTranslations("exchanges.import");
  const open = useOpenImport(projectId, start);
  const field = useId();
  const input = useRef<HTMLInputElement>(null);
  const [problem, setProblem] = useState<FileProblem>();
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  // Busy from the press to the answer, and lifted in the very update that tells it — not a
  // transition, whose end would wait for every other async action of the page (#1484).
  const [busy, setBusy] = useState(false);
  // An import lost once sent: the form waits until the screen has been read anew (US-2240).
  const reading = useReadAnew(outcome);
  const waiting = busy || reading;
  useEffect(() => {
    input.current?.focus();
  }, []);

  // The form is checked here, not by the browser: a file missing, or larger than an import
  // takes — which the server of Next would refuse before the API is asked —, is said in the page,
  // in the language of the interface, and the field keeps the focus.
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (waiting) {
      return;
    }
    const file = input.current?.files?.[0];
    if (file === undefined || file.size > IMPORT_MAX_BYTES) {
      setProblem(file === undefined ? "missing" : "tooLarge");
      input.current?.focus();
      return;
    }
    const asked =
      kind === "actual_costs"
        ? { kind, period_from: from === "" ? null : from, period_to: to === "" ? null : to }
        : { kind };
    setBusy(true);
    onSending(true);
    void open(asked, file).then((result) => {
      setBusy(false);
      onSending(false);
      if (result.kind === "done") {
        onClose();
      } else {
        setOutcome(result);
      }
    });
  };

  return (
    <form
      id={id}
      aria-label={t(`kinds.${kind}`)}
      aria-busy={waiting}
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
        <Button type="submit" size="sm" {...waitingAttributes(waiting)}>
          <WaitingIcon waiting={waiting} icon={<FileSearch aria-hidden="true" />} />
          {t("analyse")}
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          <X aria-hidden="true" />
          {t("cancel")}
        </Button>
      </div>
      <OutcomeNotice
        outcome={outcome}
        reading={reading}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
    </form>
  );
}

/**
 * What the unavailable import of actual costs lacks of the correspondence: the columns required
 * without a label, and the way to the page where they are declared (WF-REF-0190).
 */
function MappingNote({ gap }: { readonly gap: MappingGap }) {
  const t = useTranslations("exchanges.import");
  const column = useTranslations("enums.ActualCostSourceColumn");
  return (
    <p className="text-sm text-muted-foreground">
      {gap.columns.length === 0
        ? null
        : `${t("mappingMissing", {
            count: gap.columns.length,
            columns: gap.columns.map((each) => column(each)).join(", "),
          })} `}
      <Link href={gap.href} className="underline underline-offset-2">
        {t("mappingLink")}
      </Link>
    </p>
  );
}

/** The form open: its kind, and which opening it is, which a late answer is compared to (n° 24). */
interface Opened {
  readonly kind: ExchangeKind;
  readonly opening: number;
}

/** Offer the import of each kind of file, and open the choice of its file when pressed. */
export function ImportCommands({ projectId, offers, start, gap }: ImportCommandsProps) {
  const t = useTranslations("exchanges.import.kinds");
  const helps = useTranslations("commands");
  const form = useId();
  const [open, setOpen] = useState<Opened>();
  // A file is being sent: no command opens another form until the answer, as the commands of a form
  // of the risks wait for its write (`OpensForm`, #4429).
  const [sending, setSending] = useState(false);
  const buttons = useRef<Partial<Record<ExchangeKind, HTMLButtonElement | null>>>({});
  // How many times a form was opened, and which opening is open — set as it opens and closes, never
  // in an effect, which a late answer would pass before.
  const openings = useRef(0);
  const current = useRef<number>(undefined);
  const closeOpening = (opened: Opened) => {
    // The answer of a file closes the form that sent it, not the one opened since.
    if (current.current !== opened.opening) {
      return;
    }
    current.current = undefined;
    setOpen(undefined);
    buttons.current[opened.kind]?.focus();
  };
  const toggle = (kind: ExchangeKind) => {
    if (open?.kind === kind) {
      closeOpening(open);
      return;
    }
    openings.current += 1;
    current.current = openings.current;
    setOpen({ kind, opening: openings.current });
  };
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-start gap-2">
        {EXCHANGE_KINDS.map((kind) => (
          <Command
            key={kind}
            offer={offers[kind]}
            label={t(kind)}
            help={helps(`project.${IMPORT_COMMAND[kind]}.help`)}
            icon={commandIcon(PROJECT_COMMAND_ICONS[IMPORT_COMMAND[kind]])}
            writing={sending}
            disclosure={{
              expanded: open?.kind === kind,
              controls: form,
              toggle: () => {
                toggle(kind);
              },
              ref: (button) => {
                buttons.current[kind] = button;
              },
            }}
          />
        ))}
      </div>
      {gap === undefined || offers.actual_costs?.is_available !== false ? null : (
        <MappingNote gap={gap} />
      )}
      {open === undefined ? null : (
        <FileForm
          key={open.opening}
          id={form}
          kind={open.kind}
          projectId={projectId}
          start={start}
          onClose={() => {
            closeOpening(open);
          }}
          onSending={setSending}
        />
      )}
    </div>
  );
}
