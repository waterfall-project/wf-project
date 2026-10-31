// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The exits of a project from its lifecycle — completed, lost or abandoned (WF-CYC-0060) —, the
 * one command of §3.6 its screens exercise (US-0210). Pressed, an exit opens a confirmation in
 * the page — one at a time —, which names the state it leads to, that it is final, and that the
 * project and all its data become read only, a sentence that describes the field of the motive
 * and the button that confirms; it asks for the motive, if the user gives one (WF-CYC-0090). A
 * project that carries a current revision asks for its fate too: marked, with a version name and,
 * if the user gives one, a description (WF-REV-0020), or abandoned (WF-REV-0010); the API refuses
 * an exit without it. Confirmed, a server action asks the API, which judges it.
 *
 * An exit that marks answers a background task (WF-ARC-0090), handed to the tracker of the shell
 * with the exit itself, which runs it again if the task fails (WF-IHM-0080): the exit applies when
 * the task succeeds, and the page is read again then. An exit that abandons answers the state.
 *
 * The page is read again once the API has answered the exit or refused it for the state of the
 * project (409): the offers it shows are the server's again, and a confirmation whose exit is no
 * longer available closes, the focus back on its command. What the API answered stays said under
 * the command — the new state, or the refusal (`OutcomeNotice`) —, whether the confirmation is
 * still open or not.
 */
"use client";

import { X } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import { type SubmitEvent, useEffect, useId, useRef, useState } from "react";

import { type ExitResult, exitProject } from "@/api/actions/projects";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { DoneNotice } from "@/components/notices/done-notice";
import { useTrackTask, useWhenTaskSucceeds } from "@/components/tasks/task-tracker";
import type { TaskCommand } from "@/components/tasks/tracking";
import { Button } from "@/components/ui/button";
import { problemMessage } from "@/i18n/problem";
import type { ProjectState } from "@/navigation/home";

import { Command } from "./command";
import { EXIT_STATES, type ExitCommandName } from "./exits";
import { commandIcon, PROJECT_COMMAND_ICONS } from "./icons";
import type { CommandOffer } from "./offer";
import { type ObjectNames, OutcomeNotice } from "./outcome-notice";
import { rejected } from "./rejection";

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
  /** Whether the project carries a current revision, which an exit must abandon or mark. */
  readonly hasCurrentRevision: boolean;
  /** The counter of the project as the screen read it, which the exit carries. */
  readonly lockVersion: number;
}

/** An exit, whether its confirmation is the one open, and what opens and closes it. */
interface ExitCommandProps extends ExitOffer {
  readonly projectId: string;
  readonly lockVersion: number;
  readonly hasCurrentRevision: boolean;
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
  readonly lockVersion: number;
  readonly hasCurrentRevision: boolean;
  readonly onClose: () => void;
  /** The exit is applied, or — marking — its task handed to the tracker, by its identifier. */
  readonly onDone: (state: ProjectState, marking?: string) => void;
  /** What of a refusal is no field's to say: none when every refusal is said at its field. */
  readonly onRefused: (outcome: Outcome<unknown> | undefined) => void;
}

const FIELD = "w-full max-w-md rounded-md border border-input bg-background px-2 py-1";
/** What the user chose to do of the current revision; none until they choose. */
type Fate = components["schemas"]["CurrentRevisionFate"]["action"] | undefined;

/**
 * The exit as the tracker runs it again: the task it answers. An exit that answers the state
 * instead was applied in the request — the task was not needed — and is not a task to follow.
 */
function asTask(exit: () => Promise<Outcome<ExitResult>>): TaskCommand {
  return async () => {
    const outcome = await exit();
    if (outcome.kind !== "done") {
      return outcome;
    }
    return "marking" in outcome.data
      ? { kind: "done", data: outcome.data.marking }
      : { kind: "unreachable" };
  };
}
const UNAVAILABLE = "aria-disabled:cursor-not-allowed aria-disabled:opacity-50";

type FieldProblem = components["schemas"]["FieldProblem"];
/** The fields of the confirmation a refusal is said at, by the pointer the contract gives each. */
const POINTERS = {
  name: "/current_revision/version_name",
  fate: "/current_revision",
} as const;
type Field = keyof typeof POINTERS;
type Problems = Readonly<Partial<Record<Field, FieldProblem>>>;
/** The version name the user left out, found by the page itself: said as the marking says it. */
const NAME_MISSING: FieldProblem = { pointer: POINTERS.name, code: "VALUE_REQUIRED" };

/** The refusals once the user has changed a field: the one said at it goes. */
function without(problems: Problems, field: Field): Problems {
  return Object.fromEntries(Object.entries(problems).filter(([name]) => name !== field));
}

/**
 * The refusals of the API the confirmation says at a field, and the outcome to tell under the
 * command: none when every refusal is said at its field.
 */
function placed(outcome: Outcome<unknown>): {
  readonly problems: Problems;
  readonly told: Outcome<unknown> | undefined;
} {
  if (!("problem" in outcome) || outcome.problem.fields === undefined) {
    return { problems: {}, told: outcome };
  }
  let problems: Problems = {};
  const rest = outcome.problem.fields.filter((problem) => {
    const field = (Object.keys(POINTERS) as Field[]).find(
      (name) => POINTERS[name] === problem.pointer,
    );
    if (field !== undefined) {
      problems = { ...problems, [field]: problem };
    }
    return field === undefined;
  });
  if (rest.length === outcome.problem.fields.length) {
    return { problems, told: outcome };
  }
  return {
    problems,
    told:
      rest.length === 0 ? undefined : { ...outcome, problem: { ...outcome.problem, fields: rest } },
  };
}

/** Confirm an exit, with its motive if the user gives one, and ask the API for it. */
function ExitForm({
  id,
  command,
  projectId,
  lockVersion,
  hasCurrentRevision,
  onClose,
  onDone,
  onRefused,
}: ExitFormProps) {
  const t = useTranslations();
  const field = useId();
  const statement = `${field}-statement`;
  const track = useTrackTask();
  const [reason, setReason] = useState("");
  const [fate, setFate] = useState<Fate>();
  const [versionName, setVersionName] = useState("");
  const [description, setDescription] = useState("");
  const locale = useLocale();
  const messages = useMessages();
  // The refusals said at their fields, the client's own or the API's, and the field refused first,
  // which takes the focus in the commit after the one that says it: focused, it is heard with it.
  const [problems, setProblems] = useState<Problems>({});
  const [focused, setFocused] = useState<{ readonly name: Field }>();
  const nameInput = useRef<HTMLInputElement>(null);
  const firstFate = useRef<HTMLInputElement>(null);
  // Busy from the confirmation to the answer, and lifted in the very update that tells it — not a
  // transition, whose end would wait for every other async action of the page (#1484).
  const [busy, setBusy] = useState(false);
  const input = useRef<HTMLTextAreaElement>(null);
  useEffect(() => {
    input.current?.focus();
  }, []);
  useEffect(() => {
    if (focused !== undefined) {
      (focused.name === "name" ? nameInput : firstFate).current?.focus();
    }
  }, [focused]);
  const state = EXIT_STATES[command];

  /** Say the refusals at their fields, and focus the first one: the fate, then the name. */
  const refuse = (refused: Problems) => {
    setProblems(refused);
    const first =
      refused.fate === undefined ? (refused.name === undefined ? undefined : "name") : "fate";
    if (first !== undefined) {
      setFocused({ name: first });
    }
  };

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (busy) {
      return;
    }
    // The fate of the revision is the user's choice (WF-CYC-0090-A), and a marking needs its
    // version name (WF-REV-0020): the page says what lacks at its field, without asking the API.
    if (
      hasCurrentRevision &&
      (fate === undefined || (fate === "mark" && versionName.trim() === ""))
    ) {
      refuse(
        fate === undefined
          ? { fate: { pointer: POINTERS.fate, code: "VALUE_REQUIRED" } }
          : { name: NAME_MISSING },
      );
      return;
    }
    setProblems({});
    const current_revision =
      fate === "mark"
        ? {
            action: "mark" as const,
            version_name: versionName,
            ...(description === "" ? {} : { description }),
          }
        : fate === "abandon"
          ? { action: "abandon" as const }
          : undefined;
    const exit = {
      to_state: state,
      confirmed: true as const,
      lock_version: lockVersion,
      ...(reason.trim() === "" ? {} : { reason }),
      ...(hasCurrentRevision && current_revision !== undefined ? { current_revision } : {}),
    };
    const command = () => exitProject(projectId, exit);
    setBusy(true);
    void command()
      .catch(rejected)
      .then((result) => {
        setBusy(false);
        if (result.kind !== "done") {
          const refused = placed(result);
          refuse(refused.problems);
          onRefused(refused.told);
        } else if ("marking" in result.data) {
          track(result.data.marking, { command: asTask(command), subject: versionName });
          onDone(state, result.data.marking.task_id);
        } else {
          onDone(result.data.exited);
        }
      });
  };

  return (
    <form
      id={id}
      aria-label={t(`enums.ProjectCommand.${command}`)}
      aria-busy={busy}
      noValidate
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
      {hasCurrentRevision ? (
        <fieldset
          className="space-y-1"
          aria-invalid={problems.fate === undefined ? undefined : true}
          aria-describedby={problems.fate === undefined ? undefined : `${field}-fate-problem`}
        >
          <legend className="font-medium">{t("exitProject.fate")}</legend>
          {(["mark", "abandon"] as const).map((action) => (
            <label key={action} className="flex items-start gap-2">
              <input
                type="radio"
                ref={action === "mark" ? firstFate : undefined}
                name={`${field}-fate`}
                checked={fate === action}
                onChange={() => {
                  setFate(action);
                  setProblems(without(problems, "fate"));
                }}
              />
              {t(`exitProject.${action}`)}
            </label>
          ))}
          {problems.fate === undefined ? null : (
            <p id={`${field}-fate-problem`} role="alert" className="text-sm text-destructive">
              {problemMessage(problems.fate, { locale, messages })}
            </p>
          )}
          {fate === "mark" ? (
            <div className="space-y-1 pl-6">
              <label htmlFor={`${field}-version`} className="block font-medium">
                {t("exitProject.versionName")}
              </label>
              <input
                id={`${field}-version`}
                ref={nameInput}
                value={versionName}
                maxLength={100}
                aria-required
                aria-invalid={problems.name === undefined ? undefined : true}
                aria-describedby={problems.name === undefined ? undefined : `${field}-name-problem`}
                onChange={(event) => {
                  setVersionName(event.target.value);
                  setProblems(without(problems, "name"));
                }}
                className={`h-9 ${FIELD}`}
              />
              {problems.name === undefined ? null : (
                <p id={`${field}-name-problem`} role="alert" className="text-sm text-destructive">
                  {problems.name === NAME_MISSING
                    ? t("markRevision.versionNameRequired")
                    : problemMessage(problems.name, { locale, messages })}
                </p>
              )}
              <label htmlFor={`${field}-description`} className="block font-medium">
                {t("exitProject.description")}
              </label>
              <textarea
                id={`${field}-description`}
                value={description}
                rows={2}
                onChange={(event) => {
                  setDescription(event.target.value);
                }}
                className={FIELD}
              />
            </div>
          ) : null}
        </fieldset>
      ) : null}
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
          aria-disabled={busy ? true : undefined}
          className={UNAVAILABLE}
          onClick={() => {
            if (!busy) {
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

/**
 * Wait for the task that marks the revision: the exit applies when it succeeds, and the page is
 * read again, which lists the project as it now is. A task that fails applies nothing.
 */
function AppliedWhenMarked({
  task,
  onApplied,
}: {
  readonly task: string;
  readonly onApplied: () => void;
}) {
  const router = useRouter();
  useWhenTaskSucceeds(task, () => {
    onApplied();
    router.refresh();
  });
  return null;
}

/** Offer an exit of the lifecycle, open its confirmation when pressed, and say what followed. */
function ExitCommand({
  command,
  offer,
  projectId,
  lockVersion,
  hasCurrentRevision,
  names,
  open,
  onToggle,
  onClose,
}: ExitCommandProps) {
  const t = useTranslations();
  const form = useId();
  // What the exit made of the project, an object for each exit: the history notes each one.
  const [done, setDone] = useState<{ readonly state: ProjectState }>();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  // The task that marks the revision, which the exit waits for: it applies when it succeeds.
  const [marking, setMarking] = useState<{ readonly task: string; readonly state: ProjectState }>();
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
        help={t(`commands.project.${command}.help`)}
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
      {marking === undefined ? null : (
        <AppliedWhenMarked
          task={marking.task}
          onApplied={() => {
            setDone({ state: marking.state });
            setMarking(undefined);
          }}
        />
      )}
      {shown ? (
        <ExitForm
          id={form}
          command={command}
          projectId={projectId}
          lockVersion={lockVersion}
          hasCurrentRevision={hasCurrentRevision}
          onClose={close}
          onDone={(state, task) => {
            setOutcome(undefined);
            if (task === undefined) {
              setDone({ state });
            } else {
              setMarking({ task, state });
            }
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
        subject={names[projectId]}
      />
      <DoneNotice
        subject={names[projectId]}
        title={
          done === undefined
            ? undefined
            : t("exitProject.done", { state: t(`enums.ProjectState.${done.state}`) })
        }
        of={done}
      />
    </div>
  );
}

/** The exits a project offers, each in the list of its commands; one confirmation open at most. */
export function ExitCommands({
  exits,
  projectId,
  lockVersion,
  names,
  hasCurrentRevision,
}: ExitCommandsProps) {
  const [open, setOpen] = useState<ExitCommandName>();
  return exits.map(({ command, offer }) => (
    <li key={command}>
      <ExitCommand
        command={command}
        offer={offer}
        projectId={projectId}
        lockVersion={lockVersion}
        hasCurrentRevision={hasCurrentRevision}
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
