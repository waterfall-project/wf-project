// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The marking of a revision (WF-REV-0020): the command opens the entry of the version name,
 * which marking requires, then asks the API by a server action. The API gives the hand back at
 * once with a background task (WF-ARC-0090), handed to the tracker of the shell with the command
 * itself, which runs it again if it fails (WF-IHM-0080); the form closes, and the screen stays
 * as it was, usable while the revision is marked. The command waits, saying so, until the task ends
 * (`useTaskRunning`) — mounted anew, the tab reloaded or the screen left and come back to, it finds
 * the marking of its revision that still runs (`useRunningTask`, #3404) —: failed, it is given back.
 *
 * The form is part of the page, not a dialog: nothing else of the screen is withheld while it
 * is open. A refusal — a version name already taken, the revision marked meanwhile or changed
 * since it was read, the API out of reach — is told under it (`OutcomeNotice`).
 */
"use client";

import { Stamp, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState } from "react";

import { markRevision } from "@/api/actions/revisions";
import type { Outcome } from "@/api/problem";
import type { Revision } from "@/components/context/read-only";
import { useRunningTask, useTaskRunning, useTrackTask } from "@/components/tasks/task-tracker";
import { taskAim } from "@/components/tasks/tracking";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

import { Command } from "./command";
import { commandIcon, REVISION_COMMAND_ICONS } from "./icons";
import type { CommandOffer } from "./offer";
import { type ObjectNames, OutcomeNotice, useReadAnew } from "./outcome-notice";
import { rejectedWrite } from "./rejection";
import { WaitingIcon, waitingAttributes } from "./waiting";

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
  /** The marking is accepted: its task, which the command waits for, is followed. */
  readonly onMarking: (taskId: string) => void;
  /** What the API answered of a marking it did not accept, told under the form. */
  readonly outcome: Outcome<unknown> | undefined;
  readonly onOutcome: (outcome: Outcome<unknown> | undefined) => void;
  /** Whether the screen is read anew after a marking lost once sent (US-2240, `useReadAnew`). */
  readonly reading: boolean;
}

const FIELD = "max-w-sm";

const LABEL = "block text-sm font-medium";

/** What the marking aims at: its revision, by which the command finds it again (#3404). */
function markAim(revision: Revision): string {
  return taskAim("revision_mark", revision.revision_id);
}

/**
 * Ask the version name of the marking — and, if the user wishes, a description of the
 * revision —, mark, and hand the task over to the tracker.
 */
function MarkForm({
  id,
  revision,
  names,
  onClose,
  onMarking,
  outcome,
  onOutcome: setOutcome,
  reading,
}: MarkFormProps) {
  const t = useTranslations();
  const track = useTrackTask();
  const field = useId();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [missing, setMissing] = useState(false);
  // Busy from the press to the answer, and lifted in the very update that tells it — not a
  // transition, whose end would wait for every other async action of the page (#1484).
  const [busy, setBusy] = useState(false);
  const waiting = busy || reading;
  const input = useRef<HTMLInputElement>(null);
  useEffect(() => {
    input.current?.focus();
  }, []);

  // The form is checked here, not by the browser: the missing name is said in the page, in
  // the language of the interface, and the field keeps the focus.
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (waiting) {
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
    setBusy(true);
    void command()
      .catch(rejectedWrite())
      .then((result) => {
        setBusy(false);
        if (result.kind === "done") {
          track(result.data, { command, subject: name, aim: markAim(revision) });
          onMarking(result.data.task_id);
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
      aria-busy={busy}
      noValidate
      onSubmit={submit}
      className="space-y-2 rounded-md border p-3"
    >
      <label htmlFor={field} className={LABEL}>
        {t("markRevision.versionName")}
      </label>
      <Input
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
        className={FIELD}
      />
      {missing ? (
        <p id={`${field}-missing`} role="alert" className="text-sm text-destructive">
          {t("markRevision.versionNameRequired")}
        </p>
      ) : null}
      <label htmlFor={`${field}-description`} className={LABEL}>
        {t("markRevision.description")}
      </label>
      <Textarea
        id={`${field}-description`}
        value={description}
        rows={3}
        onChange={(event) => {
          setDescription(event.target.value);
        }}
        className={FIELD}
      />
      <div className="flex gap-2">
        <Button type="submit" size="sm" {...waitingAttributes(waiting)}>
          <WaitingIcon waiting={waiting} icon={<Stamp aria-hidden="true" />} />
          {t("markRevision.submit")}
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          <X aria-hidden="true" />
          {t("markRevision.cancel")}
        </Button>
      </div>
      <OutcomeNotice
        outcome={outcome}
        names={names}
        subject={names[revision.revision_id]}
        reading={reading}
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
  const helps = useTranslations("commands");
  const form = useId();
  const [open, setOpen] = useState(false);
  // The task of the last marking — else, mounted anew, the one of the revision that runs (#3404): the
  // command waits while it runs, and is given back at its end.
  const [marking, setMarking] = useState<string>();
  const found = useRunningTask(markAim(revision));
  const running = useTaskRunning(marking ?? found);
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  // A marking lost once sent: the screen is read anew before it can be asked again (US-2240) — read
  // here, where it stays mounted, so that the form closed and opened again waits as long.
  const reading = useReadAnew(outcome);
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
        help={helps("revision.mark.help")}
        icon={commandIcon(REVISION_COMMAND_ICONS.mark)}
        names={names}
        running={running}
        writing={reading}
        disclosure={{
          expanded: open,
          controls: form,
          toggle: () => {
            // Opened again, the form starts without the refusal told before, as a form mounted anew.
            if (!open) {
              setOutcome(undefined);
            }
            setOpen(!open);
          },
          ref: button,
        }}
      />
      {open ? (
        <MarkForm
          id={form}
          revision={revision}
          names={names}
          onClose={close}
          onMarking={setMarking}
          outcome={outcome}
          onOutcome={setOutcome}
          reading={reading}
        />
      ) : reading ? (
        // The form closed while the screen is read anew: the command stays unavailable, and the
        // notice of the marking that may have been done stays told as long (#3443).
        <OutcomeNotice
          outcome={outcome}
          names={names}
          subject={names[revision.revision_id]}
          reading={reading}
          onClear={() => {
            setOutcome(undefined);
          }}
        />
      ) : null}
    </div>
  );
}
