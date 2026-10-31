// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The form that declares a risk — « Identifier un risque » — or modifies one (US-0520, FBS-4.6),
 * in a dialog over the screen of the risks: the label, required; the description and the actions of
 * mitigation, as the user wrote them; the probability, entered as a percentage and sent as the
 * ratio of the contract (WF-DAT-0100); and what the provision line of the risk is written on
 * (WF-RIS-0010, EP-14/L42p, #786) — the category, among the active categories of the type provision
 * for risks, asked only when there is more than one to choose and retained without being asked
 * otherwise; the sub-project, optional, the line counting out of any sub-project without one; and
 * the task of the main structure that bears the line, optional, the first task of the first level
 * without one.
 *
 * A modification writes the fields the risk lists it may change. The category, the sub-project and
 * the task of the provision change while the risk is identified, as `update_provision` says
 * (`provisionOpen`): listed unavailable, the three are shown fixed, the conditions it lacks said
 * under the first, and none is sent. A category deactivated since the risk was declared stays among
 * the choices, said no longer admitted: kept, the server accepts it unchanged; another is a choice
 * of the active ones.
 *
 * A refusal by field (422) is said at its field — `PROVISION_CATEGORY_REQUIRED`,
 * `INACTIVE_REFERENCE_OBJECT`, `UNKNOWN_TASK`, a probability out of its bounds, said in
 * percentages as the field enters it —; any other is told under the form, which stays open to be
 * corrected: the declaration refused for want of an active category of the type provision, or of a
 * task in the main structure (409, the first condition it lacks named), the version stale (412).
 * It is `ReferenceForm` that checks, asks and tells.
 */
"use client";

import { useLocale, useTranslations } from "next-intl";

import { writeRisk } from "@/api/actions/risks";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { ANOTHER_OBJECT } from "@/components/reference/commands";
import { inPercent } from "@/components/reference/in-percent";
import {
  type Draft,
  type FormField,
  ReferenceForm,
  required,
} from "@/components/reference/reference-form";
import { editablePercent, percentRatio } from "@/i18n/format";

import { categoryChoices, type ProvisionChoice, type ProvisionOptions } from "./provision-choices";

/** A risk, as the contract gives it. */
type Risk = components["schemas"]["Risk"];

/** The longest label of a risk the contract takes. */
const LABEL_LENGTH = 300;

/** The probability, entered as a percentage: the pointer a refusal names it by. */
const PROBABILITY: ReadonlySet<string> = new Set(["/probability"]);

/** An optional text as the contract writes it: none when left empty. */
function orNull(value: string | undefined): string | null {
  return value === undefined || value === "" ? null : value;
}

/** What the form of a risk is given. */
export interface RiskFormProps {
  readonly projectId: string;
  /** The risk modified, as the screen shows it; none for a declaration. */
  readonly risk: Risk | undefined;
  /**
   * Whether the provision may be written: always for a declaration; for a modification, as the risk
   * lists `update_provision`.
   */
  readonly provisionOpen: boolean;
  /** What the provision lacks when it may not be written (`useUnmet`), said under its first field. */
  readonly unmet: string | undefined;
  readonly options: ProvisionOptions;
  /** The answer of the server, the dialog open or closed. */
  readonly onDone: (answer: Risk) => void;
  /** Told that the write leaves, then that it is answered (`ReferenceForm.onWriting`). */
  readonly onWriting?: ((writing: boolean) => void) | undefined;
  readonly onClose: () => void;
  readonly onClosed: () => void;
}

/** What the form of a risk starts from: the risk as the screen shows it, or nothing typed. */
function draftOf(risk: Risk | undefined, locale: ReturnType<typeof useLocale>): Draft {
  return risk === undefined
    ? {}
    : {
        label: risk.label,
        description: risk.description ?? "",
        mitigation_notes: risk.mitigation_notes ?? "",
        probability: editablePercent(risk.probability, locale),
        provision_cost_category_id: risk.provision_cost_category_id,
        provision_subproject_id: risk.provision_subproject_id ?? "",
        provision_task_id: risk.provision_task?.node_id ?? "",
      };
}

/** The texts the fields of the provision are labelled with. */
interface ProvisionTexts {
  readonly category: string;
  readonly subproject: string;
  readonly outOfSubproject: string;
  readonly task: string;
  readonly firstTask: string;
}

/** The choices of the provision the form asks; one not asked is `undefined`. */
interface Asked {
  readonly categories: readonly ProvisionChoice[] | undefined;
  readonly subprojects: readonly ProvisionChoice[] | undefined;
  readonly tasks: readonly ProvisionChoice[] | undefined;
}

/** A list of choices as the control takes them. */
function choicesOf(each: readonly ProvisionChoice[]): readonly (readonly [string, string])[] {
  return each.map(({ id, label }): readonly [string, string] => [id, label]);
}

/** A list of choices, if it holds more than `least`. */
function asked(
  each: readonly ProvisionChoice[],
  least: number,
): readonly ProvisionChoice[] | undefined {
  return each.length > least ? each : undefined;
}

/**
 * What the form asks of the provision, when it may be written: the category among more than one —
 * one alone is retained without being asked —, the category the risk holds among them when it is no
 * longer admitted (deactivated, or passed to another type), said so; the sub-project and the task,
 * when the project has any, the task the risk holds among them, listed or not: a choice of none
 * would move the line. A list the session may not read comes empty, and is neither asked nor
 * sent: the task held does not make it a list.
 */
function askedOf(
  risk: Risk | undefined,
  options: ProvisionOptions,
  heldLabel: string | undefined,
): Asked {
  const held =
    risk === undefined || heldLabel === undefined
      ? undefined
      : { id: risk.provision_cost_category_id, label: heldLabel };
  const task = risk?.provision_task;
  const tasks =
    task === undefined ||
    task === null ||
    options.tasks.length === 0 ||
    options.tasks.some(({ id }) => id === task.node_id)
      ? options.tasks
      : [...options.tasks, { id: task.node_id, label: task.label }];
  return {
    categories: asked(categoryChoices(options.categories, held), 1),
    subprojects: asked(options.subprojects, 0),
    tasks: asked(tasks, 0),
  };
}

/** The fields of the provision a risk may be written: those asked, each as a choice. */
function provisionFields(choices: Asked, texts: ProvisionTexts): FormField[] {
  const { categories, subprojects, tasks } = choices;
  return [
    ...(categories === undefined
      ? []
      : [
          {
            name: "provision_cost_category_id",
            label: texts.category,
            control: "choice",
            required: true,
            choices: choicesOf(categories),
          } satisfies FormField,
        ]),
    ...(subprojects === undefined
      ? []
      : [
          {
            name: "provision_subproject_id",
            label: texts.subproject,
            control: "choice",
            none: texts.outOfSubproject,
            choices: choicesOf(subprojects),
          } satisfies FormField,
        ]),
    ...(tasks === undefined
      ? []
      : [
          {
            name: "provision_task_id",
            label: texts.task,
            control: "choice",
            none: texts.firstTask,
            choices: choicesOf(tasks),
          } satisfies FormField,
        ]),
  ];
}

/**
 * The provision of a risk `update_provision` lists unavailable: its category, its sub-project and its
 * task shown fixed, the conditions it lacks said under the first, none sent.
 */
function fixedProvision(
  risk: Risk,
  heldLabel: string,
  unmet: string | undefined,
  texts: ProvisionTexts,
): FormField[] {
  const task = risk.provision_task;
  return [
    {
      name: "provision_cost_category_id",
      label: texts.category,
      control: "fixed",
      note: unmet,
      choices: [[risk.provision_cost_category_id, heldLabel]],
    },
    {
      name: "provision_subproject_id",
      label: texts.subproject,
      control: "fixed",
      choices: [
        [
          risk.provision_subproject_id ?? "",
          risk.provision_subproject_label ?? texts.outOfSubproject,
        ],
      ],
    },
    {
      name: "provision_task_id",
      label: texts.task,
      control: "fixed",
      choices: [[task?.node_id ?? "", task?.label ?? "—"]],
    },
  ];
}

/**
 * The provision the form writes: what it asks alone, none when `update_provision` is unavailable. A
 * choice of none writes none: on a modification, `null` takes the line out of its sub-project and
 * gives it back to the first task of the first level.
 */
function provisionBody(choices: Asked, draft: Draft) {
  const { provision_cost_category_id: category, provision_subproject_id: subproject } = draft;
  return {
    ...(choices.categories === undefined || category === undefined || category === ""
      ? {}
      : { provision_cost_category_id: category }),
    ...(choices.subprojects === undefined ? {} : { provision_subproject_id: orNull(subproject) }),
    ...(choices.tasks === undefined ? {} : { provision_task_id: orNull(draft.provision_task_id) }),
  };
}

/** Render the dialog that declares a risk or modifies one. */
export function RiskForm({
  projectId,
  risk,
  provisionOpen,
  unmet,
  options,
  onDone,
  onWriting,
  onClose,
  onClosed,
}: RiskFormProps) {
  const t = useTranslations("riskForm");
  const columns = useTranslations("grid.columns");
  const detail = useTranslations("risks.detail");
  const locale = useLocale();
  const texts: ProvisionTexts = {
    category: detail("provisionLine.category"),
    subproject: detail("provisionLine.subproject"),
    outOfSubproject: detail("provisionLine.outOfSubproject"),
    task: t("task"),
    firstTask: t("firstTask"),
  };
  const heldLabel =
    risk === undefined
      ? undefined
      : risk.provision_cost_category_is_active
        ? risk.provision_cost_category_label
        : detail("provisionLine.notAdmitted", { choice: risk.provision_cost_category_label });
  const none: Asked = { categories: undefined, subprojects: undefined, tasks: undefined };
  const choices = provisionOpen ? askedOf(risk, options, heldLabel) : none;
  const provision =
    provisionOpen || risk === undefined || heldLabel === undefined
      ? provisionFields(choices, texts)
      : fixedProvision(risk, heldLabel, unmet, texts);
  const fields: FormField[] = [
    required("label", columns("label"), LABEL_LENGTH),
    // The contract bounds neither the description nor the actions of mitigation (`Risk`, `RiskWrite`:
    // a string or null): no `maxLength`, the label alone has one.
    { name: "description", label: detail("description"), control: "multiline" },
    { name: "mitigation_notes", label: detail("mitigation"), control: "multiline" },
    { name: "probability", label: t("probability"), control: "number", required: true },
    ...provision,
  ];
  const ask = (values: Draft): Promise<Outcome<Risk>> => {
    const { label = "", description, mitigation_notes: mitigation, probability = "0" } = values;
    const body = {
      label,
      description: orNull(description),
      mitigation_notes: orNull(mitigation),
      probability: percentRatio(probability),
      ...provisionBody(choices, values),
    };
    return writeRisk(
      projectId,
      risk === undefined
        ? { id: undefined, body }
        : { id: risk.risk_id, body: { ...body, lock_version: risk.lock_version } },
    );
  };
  return (
    <ReferenceForm<Risk>
      kind="risk"
      title={risk === undefined ? t("identify") : t("modifyTitle", { name: risk.label })}
      hint={risk === undefined ? t("identifyHint") : t("modifyHint")}
      creating={risk === undefined}
      fields={fields}
      initial={draftOf(risk, locale)}
      subject={risk?.label}
      ask={ask}
      target={risk === undefined ? undefined : `update risk ${risk.risk_id}`}
      answering={(answer) =>
        risk !== undefined && answer.kind === "done" && answer.data.risk_id !== risk.risk_id
          ? ANOTHER_OBJECT
          : inPercent(answer, PROBABILITY)
      }
      onDone={onDone}
      onWriting={onWriting}
      onClose={onClose}
      onClosed={onClosed}
    />
  );
}
