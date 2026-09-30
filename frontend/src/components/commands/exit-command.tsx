// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * An exit of a project from its lifecycle — completed, lost or abandoned (WF-CYC-0060) —, the
 * one command of §3.6 its screens exercise (US-0210). Pressed, it opens a confirmation in the
 * page, which names the state it leads to, that it is final, and that the project and all its
 * data become read only; it asks for the motive, if the user gives one (WF-CYC-0090). Confirmed,
 * a server action asks the API, which judges it; the page is rendered again, and what the API
 * answered is said — the new state, or the refusal (`OutcomeNotice`).
 */
"use client";

import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState, useTransition } from "react";

import { exitProject } from "@/api/actions/projects";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { DoneNotice } from "@/components/account/done-notice";
import { Button } from "@/components/ui/button";

import { Command } from "./command";
import { EXIT_STATES, type ExitCommandName } from "./exits";
import { commandIcon, PROJECT_COMMAND_ICONS } from "./icons";
import type { CommandOffer } from "./offer";
import { type ObjectNames, OutcomeNotice } from "./outcome-notice";

type ProjectState = components["schemas"]["ProjectState"];

/** An exit the project offers, the project it takes out, and the names that name a conflict. */
export interface ExitCommandProps {
  readonly command: ExitCommandName;
  readonly offer: CommandOffer;
  readonly projectId: string;
  readonly names: ObjectNames;
}

/** The confirmation of an exit: what it confirms, and what closes it or follows it. */
interface ExitFormProps {
  readonly id: string;
  readonly command: ExitCommandName;
  readonly projectId: string;
  readonly names: ObjectNames;
  readonly onClose: () => void;
  readonly onDone: (state: ProjectState) => void;
}

const FIELD = "w-full max-w-md rounded-md border border-input bg-background px-2 py-1";

/** Confirm an exit, with its motive if the user gives one, and ask the API for it. */
function ExitForm({ id, command, projectId, names, onClose, onDone }: ExitFormProps) {
  const t = useTranslations();
  const field = useId();
  const [reason, setReason] = useState("");
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const input = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    input.current?.focus();
  }, []);
  const state = EXIT_STATES[command];

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    const exit = {
      to_state: state,
      confirmed: true as const,
      ...(reason.trim() === "" ? {} : { reason }),
    };
    startTransition(async () => {
      const result = await exitProject(projectId, exit);
      if (result.kind === "done") {
        onDone(result.data);
      } else {
        setOutcome(result);
      }
    });
  };

  return (
    <form
      id={id}
      aria-label={t(`enums.ProjectCommand.${command}`)}
      aria-busy={pending}
      onSubmit={submit}
      className="max-w-xl space-y-2 rounded-md border p-3 text-sm"
    >
      <p>{t("exitProject.statement", { state: t(`enums.ProjectState.${state}`) })}</p>
      <label htmlFor={field} className="block font-medium">
        {t("exitProject.reason")}
      </label>
      <textarea
        id={field}
        ref={input}
        value={reason}
        rows={3}
        onChange={(event) => {
          setReason(event.target.value);
        }}
        className={FIELD}
      />
      <div className="flex gap-2">
        <Button type="submit" size="sm">
          {commandIcon(PROJECT_COMMAND_ICONS[command])}
          {t("exitProject.submit")}
        </Button>
        <Button type="button" variant="outline" size="sm" onClick={onClose}>
          <X aria-hidden="true" />
          {t("exitProject.cancel")}
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

/** Offer an exit of the lifecycle, and open its confirmation when pressed. */
export function ExitCommand({ command, offer, projectId, names }: ExitCommandProps) {
  const t = useTranslations();
  const form = useId();
  const [open, setOpen] = useState(false);
  const [done, setDone] = useState<ProjectState>();
  const button = useRef<HTMLButtonElement>(null);
  const close = () => {
    setOpen(false);
    button.current?.focus();
  };
  return (
    <div className="space-y-2">
      <Command
        offer={offer}
        label={t(`enums.ProjectCommand.${command}`)}
        icon={commandIcon(PROJECT_COMMAND_ICONS[command])}
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
      {open ? (
        <ExitForm
          id={form}
          command={command}
          projectId={projectId}
          names={names}
          onClose={close}
          onDone={(state) => {
            setDone(state);
            close();
          }}
        />
      ) : null}
      <DoneNotice
        title={
          done === undefined
            ? undefined
            : t("exitProject.done", { state: t(`enums.ProjectState.${done}`) })
        }
      />
    </div>
  );
}
