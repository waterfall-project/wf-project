// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The form that declares a risk — « Identifier un risque » (US-0520, FBS-4.6) —, in a dialog over
 * the screen of the risks: the label, required; the description and the actions of mitigation, as
 * the user wrote them; the probability, entered as a percentage and sent as the ratio of the
 * contract (WF-DAT-0100); and what the provision line of the risk is written on (WF-RIS-0010,
 * EP-14/L42p, #786) — the category, among the active categories of the type provision for risks,
 * asked only when there is more than one to choose and retained without being asked otherwise; the
 * sub-project, optional, the line counting out of any sub-project without one; and the task of the
 * main structure that bears the line, optional, the first task of the first level without one.
 *
 * A refusal by field (422) is said at its field — `PROVISION_CATEGORY_REQUIRED`,
 * `INACTIVE_REFERENCE_OBJECT`, `UNKNOWN_TASK`, a probability out of its bounds, said in
 * percentages as the field enters it —; any other is told under the form, which stays open to be
 * corrected: the declaration refused for want of an active category of the type provision, or of a
 * task in the main structure (409, the first condition it lacks named). It is `ReferenceForm` that
 * checks, asks and tells.
 */
"use client";

import { useTranslations } from "next-intl";

import { writeRisk } from "@/api/actions/risks";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { inPercent } from "@/components/reference/in-percent";
import {
  type Draft,
  type FormField,
  ReferenceForm,
  required,
} from "@/components/reference/reference-form";
import { percentRatio } from "@/i18n/format";

import type { ProvisionChoice, ProvisionOptions } from "./provision-choices";

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
  readonly options: ProvisionOptions;
  /** The answer of the server, the dialog open or closed. */
  readonly onDone: (answer: Risk) => void;
  /** Told that the write leaves, then that it is answered (`ReferenceForm.onWriting`). */
  readonly onWriting?: ((writing: boolean) => void) | undefined;
  readonly onClose: () => void;
  readonly onClosed: () => void;
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
 * What the form asks of the provision: the category among more than one — one alone is retained
 * without being asked —, the sub-project and the task, when the project has any.
 */
function askedOf(options: ProvisionOptions): Asked {
  return {
    categories: asked(options.categories, 1),
    subprojects: asked(options.subprojects, 0),
    tasks: asked(options.tasks, 0),
  };
}

/** The fields of the provision of a risk: those asked, each as a choice. */
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

/** The provision the form writes: what it asks alone; a choice of none writes none. */
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

/** Render the dialog that declares a risk. */
export function RiskForm({
  projectId,
  options,
  onDone,
  onWriting,
  onClose,
  onClosed,
}: RiskFormProps) {
  const t = useTranslations("riskForm");
  const columns = useTranslations("grid.columns");
  const detail = useTranslations("risks.detail");
  const texts: ProvisionTexts = {
    category: detail("provisionLine.category"),
    subproject: detail("provisionLine.subproject"),
    outOfSubproject: detail("provisionLine.outOfSubproject"),
    task: t("task"),
    firstTask: t("firstTask"),
  };
  const choices = askedOf(options);
  const fields: FormField[] = [
    required("label", columns("label"), LABEL_LENGTH),
    { name: "description", label: detail("description"), control: "multiline" },
    { name: "mitigation_notes", label: detail("mitigation"), control: "multiline" },
    { name: "probability", label: t("probability"), control: "number", required: true },
    ...provisionFields(choices, texts),
  ];
  const ask = (values: Draft): Promise<Outcome<Risk>> => {
    const { label = "", description, mitigation_notes: mitigation, probability = "0" } = values;
    return writeRisk(projectId, {
      label,
      description: orNull(description),
      mitigation_notes: orNull(mitigation),
      probability: percentRatio(probability),
      ...provisionBody(choices, values),
    });
  };
  return (
    <ReferenceForm<Risk>
      kind="risk"
      title={t("identify")}
      hint={t("identifyHint")}
      creating
      fields={fields}
      initial={{}}
      ask={ask}
      target={undefined}
      answering={(answer) => inPercent(answer, PROBABILITY)}
      onDone={onDone}
      onWriting={onWriting}
      onClose={onClose}
      onClosed={onClosed}
    />
  );
}
