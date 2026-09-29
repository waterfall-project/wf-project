// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The marking of a revision (WF-REV-0020): the command opens the entry of the version name,
 * which marking requires, then asks the API by a server action. The API gives the hand back at
 * once with a background task (WF-ARC-0090), handed to the tracker of the shell with the command
 * itself, which runs it again if it fails (WF-IHM-0080); the form closes, and the screen stays
 * as it was, usable while the revision is marked.
 *
 * The form is part of the page, not a dialog: nothing else of the screen is withheld while it
 * is open. A refusal — a version name already taken, the revision marked meanwhile or changed
 * since it was read, the API out of reach — is told under it (`OutcomeNotice`).
 */
"use client";

import { useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState, useTransition } from "react";

import { markRevision } from "@/api/actions/revisions";
import type { Outcome } from "@/api/problem";
import type { Revision } from "@/components/context/read-only";
import { useTrackTask } from "@/components/tasks/task-tracker";
import { Button } from "@/components/ui/button";

import { Command } from "./command";
import type { CommandOffer } from "./offer";
import { type ObjectNames, OutcomeNotice } from "./outcome-notice";

/** The marking the revision offers, the revision, and the names that name a conflict. */
export interface MarkCommandProps {
  readonly offer: CommandOffer;
  readonly revision: Revision;
  readonly names: ObjectNames;
}

/** The form of the marking: the revision to mark, and what closes the form. */
interface MarkFormProps {
  readonly id: string;
  readonly revision: Revision;
  readonly names: ObjectNames;
  readonly onClose: () => void;
}

const FIELD = "w-full max-w-sm rounded-md border border-input bg-background px-2 text-foreground";
const LABEL = "block text-sm font-medium";

/**
 * Ask the version name of the marking — and, if the user wishes, a description of the
 * revision —, mark, and hand the task over to the tracker.
 */
function MarkForm({ id, revision, names, onClose }: MarkFormProps) {
  const t = useTranslations();
  const track = useTrackTask();
  const field = useId();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [missing, setMissing] = useState(false);
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    input.current?.focus();
  }, []);

  // The form is checked here, not by the browser: the missing name is said in the page, in
  // the language of the interface, and the field keeps the focus.
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    if (name.trim() === "") {
      setMissing(true);
      input.current?.focus();
      return;
    }
    const mark = {
      version_name: name,
      lock_version: revision.lock_version,
      ...(description === "" ? {} : { description }),
    };
    const command = () => markRevision(revision.project_id, revision.revision_id, mark);
    startTransition(async () => {
      const result = await command();
      if (result.kind === "done") {
        track(result.data, { command, subject: name });
        onClose();
      } else {
        setOutcome(result);
      }
    });
  };

  return (
    <form
      id={id}
      aria-label={t("enums.RevisionCommand.mark")}
      aria-busy={pending}
      noValidate
      onSubmit={submit}
      className="space-y-2 rounded-md border p-3"
    >
      <label htmlFor={field} className={LABEL}>
        {t("markRevision.versionName")}
      </label>
      <input
        id={field}
        ref={input}
        value={name}
        required
        maxLength={100}
        aria-invalid={missing ? true : undefined}
        aria-describedby={missing ? `${field}-missing` : undefined}
        onChange={(event) => {
          setName(event.target.value);
          setMissing(false);
        }}
        className={`h-9 ${FIELD}`}
      />
      {missing ? (
        <p id={`${field}-missing`} role="alert" className="text-sm text-destructive">
          {t("markRevision.versionNameRequired")}
        </p>
      ) : null}
      <label htmlFor={`${field}-description`} className={LABEL}>
        {t("markRevision.description")}
      </label>
      <textarea
        id={`${field}-description`}
        value={description}
        rows={3}
        onChange={(event) => {
          setDescription(event.target.value);
        }}
        className={`py-1 ${FIELD}`}
      />
      <div className="flex gap-2">
        <Button type="submit" size="sm">
          {t("markRevision.submit")}
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          {t("markRevision.cancel")}
        </Button>
      </div>
      <OutcomeNotice
        outcome={outcome}
        names={names}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
    </form>
  );
}

/** Offer the marking of a revision, and open the entry of its version name when pressed. */
export function MarkCommand({ offer, revision, names }: MarkCommandProps) {
  const t = useTranslations("enums.RevisionCommand");
  const form = useId();
  const [open, setOpen] = useState(false);
  const button = useRef<HTMLButtonElement>(null);
  const close = () => {
    setOpen(false);
    button.current?.focus();
  };
  return (
    <div className="space-y-2">
      <Command
        offer={offer}
        label={t("mark")}
        names={names}
        disclosure={{
          expanded: open,
          controls: form,
          toggle: () => {
            setOpen(!open);
          },
          ref: button,
        }}
      />
      {open ? <MarkForm id={form} revision={revision} names={names} onClose={close} /> : null}
    </div>
  );
}
