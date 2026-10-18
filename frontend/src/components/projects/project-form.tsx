// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands that write a project itself (EP-02/L44a), in the dialog of the forms of the
 * reference data (`ReferenceForm`): its creation, on the home, and the modification of its identity
 * and its facts, on its settings (FBS-4.2).
 *
 * The creation is offered to a session that holds the permission of its own (`project_create`,
 * WF-ADM-0100), which the page reads in the session and hands over as data; unavailable while the
 * minimum reference data is incomplete (`getReferenceReadiness`, WF-CYC-0120), the server refusing it
 * then — described by the refusal it would meet, the prerequisites named by the notice of the home
 * above the list. It takes what
 * `ProjectCreate` takes — the label, required (WF-PRJ-0080), the code, which may wait for the order
 * (WF-PRJ-0010), and the description —, and leads to the project the server created, its creator
 * its project manager (WF-PRJ-0060) — as long as the home is still shown: a creation answered once
 * the user has gone elsewhere does not take the place of the navigation they chose.
 *
 * The modification follows the command the project lists (`update`, `available_commands`): absent,
 * available, or unavailable with the conditions it lacks — a terminal project (WF-CYC-0100). It
 * takes what `ProjectUpdate` takes: the label, the code, the description, the date the order was
 * received — which no transition requires (WF-PRJ-0080) —, the inflation rate and the probability of
 * winning, both entered as percentages and sent as the ratios of the contract. The probability
 * follows a command of its own (`update_win_probability`, EP-14/L42i), frozen from the state in
 * progress (WF-PRJ-0090): listed unavailable, the field is shown fixed, the conditions it lacks said
 * under it, and the value is not sent. The answer takes the place of what the screen shows as
 * long as it is newer than the project the page read (`lock_version`) — against the fake back, which
 * keeps nothing, for as long as the screen stays; the settings say so once, under their header
 * (`MockupNotice`) —, and the page is read anew. The form writes from the version it opened on, as the
 * lists of the reference data do (`CommandedList`, `opened`): a reading that comes while it is open
 * does not lend its `lock_version` to a draft entered on another, which the optimistic lock
 * refuses; and the command waits while a write of a dialog closed is under way, for the form to
 * open on the version its answer brings (#661, #673).
 *
 * A refusal by field is said at its field — a code another project bears (409), named by the label
 * the refusal gives it, the screen not showing the other projects; a rate out of its bounds (422),
 * the bound said in percentages as the field enters it —, any other under the form — the probability
 * frozen meanwhile (409, the condition it lacks named), the version stale (412) with the offer to read
 * the page anew; a refusal answered once the dialog is gone is told above the facts (`Reactivations`).
 */
"use client";

import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";

import { createProject, updateProject } from "@/api/actions/projects";
import type { Outcome } from "@/api/problem";
import { Command, useUnmet } from "@/components/commands/command";
import { commandIcon, PROJECT_COMMAND_ICONS } from "@/components/commands/icons";
import { type CommandOffer, findOffer, UNAVAILABLE } from "@/components/commands/offer";
import type { Project } from "@/components/context/reading";
import { ANOTHER_OBJECT } from "@/components/reference/commands";
import { Reactivations } from "@/components/reference/reactivation";
import {
  type Draft,
  type FormField,
  ReferenceForm,
  required,
  WritingNote,
} from "@/components/reference/reference-form";
import { Button } from "@/components/ui/button";
import { editablePercent, percentRatio, ratioPercent } from "@/i18n/format";

import { SettingsFacts } from "./project-facts";

/** The longest label and code of a project the contract takes. */
const LABEL_LENGTH = 300;
const CODE_LENGTH = 50;

/** The rates of a project, entered as percentages, which the server bounds as ratios (EP-14/L42i). */
const RATES: ReadonlySet<string> = new Set(["/inflation_rate", "/win_probability"]);

/** The bounds a refusal by field may name. */
const BOUNDS: ReadonlySet<string> = new Set(["minimum", "maximum"]);

/** An optional text as the contract writes it: none when left empty. */
function orNull(value: string | undefined): string | null {
  return value === undefined || value === "" ? null : value;
}

/** What a project is created from, and the facts of its identity it shares with a modification. */
function useIdentityFields(): FormField[] {
  const t = useTranslations("projectForm");
  return [
    required("label", t("label"), LABEL_LENGTH),
    { name: "code", label: t("code"), control: "text", maxLength: CODE_LENGTH },
    { name: "description", label: t("description"), control: "text" },
  ];
}

/**
 * The command that creates a project, and its form, on the home; unavailable, and saying why, while
 * the minimum reference data is incomplete.
 */
export function CreateProject({ ready }: { readonly ready: boolean }) {
  const t = useTranslations("projectForm");
  const errors = useTranslations("errors");
  const router = useRouter();
  const identity = useIdentityFields();
  const why = useId();
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  // Whether the home is still shown, which a creation answered leads from.
  const shown = useRef(true);
  useEffect(() => {
    shown.current = true;
    return () => {
      shown.current = false;
    };
  }, []);
  return (
    <Reactivations reads={[]}>
      <Button
        ref={trigger}
        type="button"
        variant="outline"
        size="sm"
        aria-disabled={ready ? undefined : true}
        aria-describedby={ready ? undefined : why}
        className={UNAVAILABLE}
        onClick={() => {
          setOpen(ready);
        }}
      >
        <Plus aria-hidden="true" />
        {t("create")}
      </Button>
      {ready ? null : (
        <p id={why} className="max-w-64 text-xs text-muted-foreground">
          {errors("REFERENCE_INCOMPLETE")}
        </p>
      )}
      {open ? (
        <ReferenceForm<Project>
          kind="project"
          title={t("create")}
          hint={t("createHint")}
          creating
          fields={identity}
          initial={{}}
          ask={({ label = "", code, description }) =>
            createProject({ label, code: orNull(code), description: orNull(description) })
          }
          target={undefined}
          answering={(answer) => answer}
          onDone={(project) => {
            if (!shown.current) {
              return;
            }
            setOpen(false);
            router.push(`/projects/${project.project_id}`);
          }}
          onClose={() => {
            setOpen(false);
          }}
          onClosed={() => trigger.current?.focus()}
        />
      ) : null}
    </Reactivations>
  );
}

/**
 * A refusal of the rates as the form says it: each bound the server names in a ratio (`1`), said in
 * the percentage the field enters (`100`); any other answer as it is.
 */
function inPercent(answer: Outcome<Project>): Outcome<Project> {
  if (!("problem" in answer) || answer.problem.fields === undefined) {
    return answer;
  }
  const fields = answer.problem.fields.map((field) =>
    RATES.has(field.pointer) && field.params !== undefined
      ? {
          ...field,
          params: Object.fromEntries(
            Object.entries(field.params).map(([key, value]) => [
              key,
              BOUNDS.has(key) && typeof value === "string" ? (ratioPercent(value) ?? value) : value,
            ]),
          ),
        }
      : field,
  );
  return { ...answer, problem: { ...answer.problem, fields } };
}

/**
 * The field of the probability of winning, as the project lists its command
 * (`update_win_probability`): a number, available; shown fixed otherwise, the conditions it lacks
 * said under it.
 */
function useWinProbabilityField(): (offer: CommandOffer | undefined) => FormField {
  const t = useTranslations("projectForm");
  const unmet = useUnmet();
  return (offer) => {
    const shared = { name: "win_probability", label: t("winProbability") };
    if (offer?.is_available === true) {
      return { ...shared, control: "number", required: true };
    }
    const lacking = offer !== undefined && offer.missing_conditions.length > 0;
    return { ...shared, control: "fixed", note: lacking ? unmet(offer) : undefined };
  };
}

/** What the modification of a project starts from: the project as the screen shows it. */
function draftOf(project: Project, locale: ReturnType<typeof useLocale>): Draft {
  return {
    label: project.label,
    code: project.code ?? "",
    description: project.description ?? "",
    order_received_on: project.order_received_on ?? "",
    inflation_rate: editablePercent(project.inflation_rate, locale),
    win_probability: editablePercent(project.win_probability, locale),
  };
}

/** The form that modifies the identity and the facts of a project, from the version it opened on. */
function UpdateForm({
  project,
  onDone,
  onWriting,
  onClose,
  onClosed,
}: {
  readonly project: Project;
  readonly onDone: (answer: Project) => void;
  readonly onWriting: (writing: boolean) => void;
  readonly onClose: () => void;
  readonly onClosed: () => void;
}) {
  const t = useTranslations("projectForm");
  const locale = useLocale();
  const identity = useIdentityFields();
  const probability = useWinProbabilityField();
  const offer = findOffer(project.available_commands, "update_win_probability");
  const open = offer?.is_available === true;
  const fields: FormField[] = [
    ...identity,
    { name: "order_received_on", label: t("orderReceivedOn"), control: "date" },
    { name: "inflation_rate", label: t("inflationRate"), control: "number", required: true },
    probability(offer),
  ];
  const ask = ({
    label = "",
    code,
    description,
    order_received_on: received,
    inflation_rate: inflation = "0",
    win_probability: winProbability = "0",
  }: Draft): Promise<Outcome<Project>> =>
    updateProject(project.project_id, {
      label,
      code: orNull(code),
      description: orNull(description),
      order_received_on: orNull(received),
      inflation_rate: percentRatio(inflation),
      // Frozen as its command says: not sent, the server would refuse it.
      ...(open ? { win_probability: percentRatio(winProbability) } : {}),
      lock_version: project.lock_version,
    });
  return (
    <ReferenceForm<Project>
      kind="project"
      title={t("modifyTitle", { name: project.label })}
      hint={t("modifyHint")}
      creating={false}
      fields={fields}
      initial={draftOf(project, locale)}
      ask={ask}
      target={`update project ${project.project_id}`}
      answering={(answer) =>
        answer.kind === "done" && answer.data.project_id !== project.project_id
          ? ANOTHER_OBJECT
          : inPercent(answer)
      }
      onDone={onDone}
      onWriting={onWriting}
      onClose={onClose}
      onClosed={onClosed}
    />
  );
}

/** The version a form opened on, which it writes from, and the how-many-th opening it is. */
interface Editing {
  readonly project: Project;
  readonly opening: number;
}

/** What the last modification did, and the how-many-th it was. */
interface Said {
  readonly text: string;
  readonly count: number;
}

/**
 * The identity and the facts of a project on its settings, the command that modifies them as the
 * project lists it, and its form; the answer of the server shown while it is newer than the project
 * read. The command waits, inactive and saying why, for the answer of a write under way, which
 * brings the version (#661); an answer closes only the opening of the form it was sent from (#660),
 * a guard the waiting command leaves without use.
 */
export function ProjectIdentity({ project }: { readonly project: Project }) {
  const t = useTranslations("projectForm");
  const command = useTranslations("enums.ProjectCommand");
  const [answered, setAnswered] = useState<Project>();
  // The version the form opened on, which it writes from, and its opening: none while it is closed.
  const [editing, setEditing] = useState<Editing>();
  // How many times the form was opened: what tells an opening from the next.
  const openings = useRef(0);
  // Whether a write is under way: the command waits for its answer, which brings the version.
  const [writing, setWriting] = useState(false);
  const [said, setSaid] = useState<Said>();
  const trigger = useRef<HTMLButtonElement>(null);
  const why = useId();
  // An answer is for this project alone — the page keys the section by it, and an answer for
  // another is a failure of the service (`ANOTHER_OBJECT`) —, shown while newer than the reading.
  const shown =
    answered !== undefined && answered.lock_version > project.lock_version ? answered : project;
  const offer = findOffer(shown.available_commands, "update");
  const icon = commandIcon(PROJECT_COMMAND_ICONS.update);
  return (
    <Reactivations reads={[]}>
      <div className="flex flex-wrap items-start gap-2">
        <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
          {said === undefined ? null : <span key={said.count}>{said.text}</span>}
        </p>
        {offer?.is_available === true ? (
          <Button
            ref={trigger}
            type="button"
            variant="outline"
            size="sm"
            aria-disabled={writing ? true : undefined}
            aria-busy={writing}
            aria-describedby={writing ? why : undefined}
            className={UNAVAILABLE}
            onClick={() => {
              if (writing) {
                return;
              }
              openings.current += 1;
              setEditing({ project: shown, opening: openings.current });
            }}
          >
            {icon}
            {command("update")}
          </Button>
        ) : (
          <Command offer={offer} label={command("update")} icon={icon} />
        )}
        <WritingNote id={why} writing={writing} />
      </div>
      <SettingsFacts project={shown} />
      {editing === undefined ? null : (
        <UpdateForm
          key={editing.opening}
          project={editing.project}
          onDone={(answer) => {
            setAnswered((before) =>
              before === undefined || before.lock_version < answer.lock_version ? answer : before,
            );
            setSaid((before) => ({ text: t("saved"), count: (before?.count ?? 0) + 1 }));
            // Closed if it is still the opening the answer was sent from, never a later one: a guard
            // of the waiting command (`onWriting`), which serves in no normal use — no other opening
            // can come before the answer.
            const { opening } = editing;
            setEditing((current) => (current?.opening === opening ? undefined : current));
          }}
          onWriting={setWriting}
          onClose={() => {
            setEditing(undefined);
          }}
          onClosed={() => trigger.current?.focus()}
        />
      )}
    </Reactivations>
  );
}
