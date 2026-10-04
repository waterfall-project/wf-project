// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The exits of a project from its lifecycle — completed, lost or abandoned (WF-CYC-0060) —, the
 * one command of §3.6 its screens exercise (US-0210). Pressed, an exit opens a confirmation in
 * the page — one at a time —, which names the state it leads to, that it is final, and that the
 * project and all its data become read only, a sentence that describes the field of the motive
 * and the button that confirms; it asks for the motive, if the user gives one (WF-CYC-0090).
 * Confirmed, a server action asks the API, which judges it.
 *
 * The page is read again once the API has answered the exit or refused it for the state of the
 * project (409): the offers it shows are the server's again, and a confirmation whose exit is no
 * longer available closes, the focus back on its command. What the API answered stays said under the command — the new state,
 * or the refusal (`OutcomeNotice`) —, whether the confirmation is still open or not.
 */
"use client";

import { X } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState, useTransition } from "react";

import { exitProject } from "@/api/actions/projects";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { DoneNotice } from "@/components/notices/done-notice";
import { Button } from "@/components/ui/button";

import { Command } from "./command";
import { EXIT_STATES, type ExitCommandName } from "./exits";
import { commandIcon, PROJECT_COMMAND_ICONS } from "./icons";
import type { CommandOffer } from "./offer";
import { type ObjectNames, OutcomeNotice } from "./outcome-notice";

type ProjectState = components["schemas"]["ProjectState"];

/** An exit the project lists, and what it offers of it. */
export interface ExitOffer {
  readonly command: ExitCommandName;
  readonly offer: CommandOffer;
}

/** The exits a project offers, the project, and the names that name a conflict. */
export interface ExitCommandsProps {
  readonly exits: readonly ExitOffer[];
  readonly projectId: string;
  readonly names: ObjectNames;
}

/** An exit, whether its confirmation is the one open, and what opens and closes it. */
interface ExitCommandProps extends ExitOffer {
  readonly projectId: string;
  readonly names: ObjectNames;
  readonly open: boolean;
  readonly onToggle: () => void;
  readonly onClose: () => void;
}

/** The confirmation of an exit: what it confirms, and what closes it or follows it. */
interface ExitFormProps {
  readonly id: string;
  readonly command: ExitCommandName;
  readonly projectId: string;
  readonly onClose: () => void;
  readonly onDone: (state: ProjectState) => void;
  readonly onRefused: (outcome: Outcome<unknown>) => void;
}

const FIELD = "w-full max-w-md rounded-md border border-input bg-background px-2 py-1";
const UNAVAILABLE = "aria-disabled:cursor-not-allowed aria-disabled:opacity-50";

/** Confirm an exit, with its motive if the user gives one, and ask the API for it. */
function ExitForm({ id, command, projectId, onClose, onDone, onRefused }: ExitFormProps) {
  const t = useTranslations();
  const field = useId();
  const statement = `${field}-statement`;
  const [reason, setReason] = useState("");
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
        onRefused(result);
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
      <p id={statement}>
        {t("exitProject.statement", { state: t(`enums.ProjectState.${state}`) })}
      </p>
      <label htmlFor={field} className="block font-medium">
        {t("exitProject.reason")}
      </label>
      <textarea
        id={field}
        ref={input}
        value={reason}
        rows={3}
        aria-describedby={statement}
        onChange={(event) => {
          setReason(event.target.value);
        }}
        className={FIELD}
      />
      <div className="flex gap-2">
        <Button type="submit" size="sm" aria-describedby={statement}>
          {commandIcon(PROJECT_COMMAND_ICONS[command])}
          {t("exitProject.submit")}
        </Button>
        {/* While the API is asked, the confirmation stays: its answer is said under it. */}
        <Button
          type="button"
          variant="outline"
          size="sm"
          aria-disabled={pending ? true : undefined}
          className={UNAVAILABLE}
          onClick={() => {
            if (!pending) {
              onClose();
            }
          }}
        >
          <X aria-hidden="true" />
          {t("exitProject.cancel")}
        </Button>
      </div>
    </form>
  );
}

/** Offer an exit of the lifecycle, open its confirmation when pressed, and say what followed. */
function ExitCommand({
  command,
  offer,
  projectId,
  names,
  open,
  onToggle,
  onClose,
}: ExitCommandProps) {
  const t = useTranslations();
  const form = useId();
  const [done, setDone] = useState<ProjectState>();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const button = useRef<HTMLButtonElement>(null);
  // The page read again may no longer offer the exit: its confirmation closes.
  const shown = open && offer.is_available;
  const withdrawn = open && !offer.is_available;
  const close = () => {
    onClose();
    button.current?.focus();
  };
  // Withdrawn, the confirmation took the focus away with it: the focus comes back to the
  // command, unless the user has put it elsewhere meanwhile.
  useEffect(() => {
    if (!withdrawn) {
      return;
    }
    onClose();
    if (document.activeElement === null || document.activeElement === document.body) {
      button.current?.focus();
    }
  }, [withdrawn, onClose]);
  return (
    <div className="space-y-2">
      <Command
        offer={offer}
        label={t(`enums.ProjectCommand.${command}`)}
        icon={commandIcon(PROJECT_COMMAND_ICONS[command])}
        names={names}
        disclosure={{
          expanded: shown,
          controls: form,
          toggle: () => {
            if (!open) {
              setOutcome(undefined);
            }
            onToggle();
          },
          ref: button,
        }}
      />
      {shown ? (
        <ExitForm
          id={form}
          command={command}
          projectId={projectId}
          onClose={close}
          onDone={(state) => {
            setDone(state);
            setOutcome(undefined);
            close();
          }}
          onRefused={setOutcome}
        />
      ) : null}
      <OutcomeNotice
        outcome={outcome}
        names={names}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
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

/** The exits a project offers, each in the list of its commands; one confirmation open at most. */
export function ExitCommands({ exits, projectId, names }: ExitCommandsProps) {
  const [open, setOpen] = useState<ExitCommandName>();
  return exits.map(({ command, offer }) => (
    <li key={command}>
      <ExitCommand
        command={command}
        offer={offer}
        projectId={projectId}
        names={names}
        open={open === command}
        onToggle={() => {
          setOpen(open === command ? undefined : command);
        }}
        onClose={() => {
          setOpen(undefined);
        }}
      />
    </li>
  ));
}
