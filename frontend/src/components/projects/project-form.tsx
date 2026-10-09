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
 * winning, both entered as percentages and sent as the ratios of the contract. The probability is
 * frozen from the state in progress, as the contract says (`Project.win_probability`, WF-PRJ-0090):
 * the form no longer offers it, and says why. The answer takes the place of what the screen shows as
 * long as it is newer than the project the page read (`lock_version`) — against the fake back, which
 * keeps nothing, for as long as the screen stays; the settings say so once, under their header
 * (`MockupNotice`) —, and the page is read anew. The form writes from the version it opened on, as the
 * lists of the reference data do (`CommandedList`, `opened`): a reading that comes while it is open
 * does not lend its `lock_version` to a draft entered on another, which the optimistic lock refuses.
 *
 * A refusal by field is said at its field — a code another project bears (409), the probability
 * frozen meanwhile —, any other under the form, the version stale (412) with the offer to read the
 * page anew; a refusal answered once the dialog is gone is told above the facts (`Reactivations`).
 */
"use client";

import { Plus } from "lucide-react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { useEffect, useId, useRef, useState } from "react";

import { createProject, updateProject } from "@/api/actions/projects";
import type { Outcome } from "@/api/problem";
import { Command } from "@/components/commands/command";
import { commandIcon, PROJECT_COMMAND_ICONS } from "@/components/commands/icons";
import { findOffer, UNAVAILABLE } from "@/components/commands/offer";
import type { Project } from "@/components/context/reading";
import { ANOTHER_OBJECT } from "@/components/reference/commands";
import { Reactivations } from "@/components/reference/reactivation";
import {
  type Draft,
  type FormField,
  ReferenceForm,
  required,
} from "@/components/reference/reference-form";
import { Button } from "@/components/ui/button";
import { editablePercent, percentRatio } from "@/i18n/format";
import type { ProjectState } from "@/navigation/home";

import { SettingsFacts } from "./project-facts";

/** The longest label and code of a project the contract takes. */
const LABEL_LENGTH = 300;
const CODE_LENGTH = 50;

/** The states in which the probability of winning may still be modified (WF-PRJ-0090). */
const WIN_PROBABILITY_OPEN: readonly ProjectState[] = ["created", "pricing"];

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
  onClose,
  onClosed,
}: {
  readonly project: Project;
  readonly onDone: (answer: Project) => void;
  readonly onClose: () => void;
  readonly onClosed: () => void;
}) {
  const t = useTranslations("projectForm");
  const locale = useLocale();
  const identity = useIdentityFields();
  const open = WIN_PROBABILITY_OPEN.includes(project.state);
  const fields: FormField[] = [
    ...identity,
    { name: "order_received_on", label: t("orderReceivedOn"), control: "date" },
    { name: "inflation_rate", label: t("inflationRate"), control: "number", required: true },
    ...(open
      ? [
          {
            name: "win_probability",
            label: t("winProbability"),
            control: "number",
            required: true,
          } as const,
        ]
      : []),
  ];
  const ask = ({
    label = "",
    code,
    description,
    order_received_on: received,
    inflation_rate: inflation = "0",
    win_probability: probability = "0",
  }: Draft): Promise<Outcome<Project>> =>
    updateProject(project.project_id, {
      label,
      code: orNull(code),
      description: orNull(description),
      order_received_on: orNull(received),
      inflation_rate: percentRatio(inflation),
      // Frozen from the state in progress: not sent, the server would refuse it.
      ...(open ? { win_probability: percentRatio(probability) } : {}),
      lock_version: project.lock_version,
    });
  return (
    <ReferenceForm<Project>
      kind="project"
      title={t("modifyTitle", { name: project.label })}
      hint={t(open ? "modifyHint" : "modifyHintFrozen")}
      creating={false}
      fields={fields}
      initial={draftOf(project, locale)}
      ask={ask}
      target={`update project ${project.project_id}`}
      answering={(answer) =>
        answer.kind === "done" && answer.data.project_id !== project.project_id
          ? ANOTHER_OBJECT
          : answer
      }
      onDone={onDone}
      onClose={onClose}
      onClosed={onClosed}
    />
  );
}

/** What the last modification did, and the how-many-th it was. */
interface Said {
  readonly text: string;
  readonly count: number;
}

/**
 * The identity and the facts of a project on its settings, the command that modifies them as the
 * project lists it, and its form; the answer of the server shown while it is newer than the project
 * read.
 */
export function ProjectIdentity({ project }: { readonly project: Project }) {
  const t = useTranslations("projectForm");
  const command = useTranslations("enums.ProjectCommand");
  const [answered, setAnswered] = useState<Project>();
  // The version the form opened on, which it writes from: none while it is closed.
  const [editing, setEditing] = useState<Project>();
  const [said, setSaid] = useState<Said>();
  const trigger = useRef<HTMLButtonElement>(null);
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
            onClick={() => {
              setEditing(shown);
            }}
          >
            {icon}
            {command("update")}
          </Button>
        ) : (
          <Command offer={offer} label={command("update")} icon={icon} />
        )}
      </div>
      <SettingsFacts project={shown} />
      {editing === undefined ? null : (
        <UpdateForm
          project={editing}
          onDone={(answer) => {
            setAnswered((before) =>
              before === undefined || before.lock_version < answer.lock_version ? answer : before,
            );
            setSaid((before) => ({ text: t("saved"), count: (before?.count ?? 0) + 1 }));
            setEditing(undefined);
          }}
          onClose={() => {
            setEditing(undefined);
          }}
          onClosed={() => trigger.current?.focus()}
        />
      )}
    </Reactivations>
  );
}
