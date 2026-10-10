// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The form that creates or modifies an object of the reference data, in a dialog over its list
 * (EP-02/L43) — or a project, its identity and its facts (EP-02/L44a), or a sub-project of a project
 * (EP-02/L44b), or the settings of the risks or of the indicators (EP-14/L43e) —: the fields of its
 * kind, each by the pointer of the contract it writes (`code`, `capacity/monthly_hours`), a text, a
 * number, a date of planning or a choice — or a value the object lists no command to change, shown
 * fixed, read-only, and sent as it is (EP-02/L42g). A field may say a note under it, which describes
 * it: why it is fixed, or why its choices are fewer. Fields that go together — the three bounds of an
 * axis, the zones of a level of probability — are set side by side under the legend of their group
 * (`group`).
 *
 * The form is checked here before anything is asked: a field required left empty, a number that is
 * not one in the language of the reader (`parseDecimal`), a date that is none (`isPlanningDate`), is
 * said at the field, which takes the focus; then the rules that bind fields to one another (`rules`) —
 * bounds in their order, an alert below its watch —, each broken one said at the field that breaks it,
 * as the server would point at it. The rest is the server's to judge: a refusal by field (422,
 * `fields[]`, convention #293) is said at each field it points at, by the sentence of its code and its parameters
 * (`problemMessage`), the first field refused taking the focus — a value already held (409
 * `ALREADY_EXISTS`, `fields[]`) too, which names the object that holds it as the list shows it
 * (`names`), by the label the refusal gives it when the list does not show it
 * (`conflicting_object_label`, EP-14/L42i), or generically without either (WF-REF-0030,
 * WF-REF-0040); any other refusal — a state that forbids the write (409) with the condition it lacks,
 * the version stale (412) with the offer to read the page anew, the API out of reach, a field the form
 * does not show — is told under the form (`OutcomeNotice`), which stays open to be corrected, without
 * what is said at the fields already.
 *
 * The button that sends says the write under way. The dialog may be closed meanwhile: the answer of
 * the server is handed back all the same (`onDone`), and a refusal is told above the list, on the
 * reading the form was sent from (`useListReport`) — what the server did is never left unsaid.
 */
"use client";

import { Plus, Save, X } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState, useTransition } from "react";

import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { type ObjectNames, OutcomeNotice } from "@/components/commands/outcome-notice";
import { rejected } from "@/components/commands/rejection";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { isPlanningDate, parseDecimal } from "@/i18n/format";
import { problemMessage } from "@/i18n/problem";

import type { ListForm } from "./commands";
import type { ReferenceObject } from "./kinds";
import { useListReport } from "./reactivation";

/** A refusal of one field, by the server or by the form. */
type FieldProblem = components["schemas"]["FieldProblem"];

/** The longest code and name of an object of the reference data the contract takes. */
export const CODE_LENGTH = 20;
export const LABEL_LENGTH = 200;

/** A field of a form, by the pointer of the contract it writes, without its first slash. */
export interface FormField {
  readonly name: string;
  readonly label: string;
  /**
   * A text, a number, a whole number — a count, sent as its digits —, a date of planning, a choice,
   * or a value shown fixed — read-only, by the text of its choice.
   */
  readonly control: "text" | "number" | "whole" | "date" | "choice" | "fixed";
  readonly required?: boolean;
  /** The longest text the contract takes. */
  readonly maxLength?: number;
  /** The values a choice offers, each with its text, in their order; a fixed value shown by its own. */
  readonly choices?: readonly (readonly [string, string])[];
  /** What is said under the field, which describes it: why it is fixed, or offers fewer choices. */
  readonly note?: string | undefined;
  /** The text of the choice of none — a root for the parent of a node —; « Choose… » otherwise. */
  readonly none?: string;
  /**
   * The legend of the fields that go together, set side by side: those next to it that share it. It
   * starts the name of each, which its label alone repeats from one group to the next.
   */
  readonly group?: string;
  /** What is said of a value the field refuses as malformed, rather than the sentence of its code. */
  readonly invalid?: string;
}

/** A field of text the form requires, no longer than the contract takes. */
export function required(name: string, label: string, maxLength: number): FormField {
  return { name, label, control: "text", required: true, maxLength };
}

/** What a form holds, by the name of each field. */
export type Draft = Readonly<Record<string, string>>;

/**
 * What a form writes, and how: an object of the reference data, unless it names another of the
 * contract — a project, or a sub-project.
 */
export interface ReferenceFormProps<T = ReferenceObject> extends Pick<
  ListForm,
  "target" | "onClose" | "onClosed"
> {
  /**
   * What the form writes: a kind of object of the reference data, a project, a sub-project or the
   * settings of the installation — what names the holder of a value already taken when neither the
   * list nor the refusal does (`takenByAnother`).
   */
  readonly kind: ListForm["kind"] | "project" | "subproject" | "settings";
  readonly title: string;
  readonly hint: string;
  /** Whether the form creates an object rather than modifies one. */
  readonly creating: boolean;
  readonly fields: readonly FormField[];
  /** What the form starts from: the object modified, or nothing typed. */
  readonly initial: Draft;
  /**
   * The names of the objects the list shows, by identifier: what names the object that holds a value
   * already taken (409 `ALREADY_EXISTS`); none, and it is said generically.
   */
  readonly names?: ObjectNames | undefined;
  /**
   * Ask the server, from the values checked: a text trimmed, a number as the contract writes it, a
   * choice as chosen — none an empty text.
   */
  readonly ask: (values: Draft) => Promise<Outcome<T>>;
  /**
   * The rules that bind fields to one another, judged once every field is checked, on the values as
   * the contract writes them: a refusal at each field that breaks one; none, and the form asks.
   */
  readonly rules?: ((values: Draft) => ReadonlyMap<string, FieldProblem>) | undefined;
  /** The answer of the server as the form takes it (`ListForm.answering`). */
  readonly answering: (answer: Outcome<T>) => Outcome<T>;
  /** Take the answer of the server, the dialog open or closed. */
  readonly onDone: (answer: T) => void;
}

/**
 * A number typed, as the contract writes it — a decimal in the language of the reader
 * (`parseDecimal`), a whole number as its digits alone —, or `undefined` when it is none; any other
 * value as it is.
 */
function numeric(
  control: FormField["control"],
  value: string,
  locale: ReturnType<typeof useLocale>,
): string | undefined {
  if (value === "") {
    return value;
  }
  if (control === "whole") {
    return /^\d+$/.test(value) ? value : undefined;
  }
  return control === "number" ? parseDecimal(value, locale) : value;
}

/**
 * A field judged before asking: its value as the contract writes it — a text trimmed, a number as the
 * contract writes it, a choice or a fixed value as it is —, or why it is refused: a date half
 * entered, which its control gives as an empty text (`badInput`) and which would otherwise leave as
 * none, a field required left empty, a number that is not one in the language of the reader
 * (`parseDecimal`), a whole number that is not digits alone, a date that is none (`isPlanningDate`).
 */
function judged(
  { control, required }: FormField,
  typed: string,
  locale: ReturnType<typeof useLocale>,
  badInput: boolean,
): { readonly value: string } | { readonly code: FieldProblem["code"] } {
  const value = control === "choice" || control === "fixed" ? typed : typed.trim();
  if (control === "date" && badInput) {
    return { code: "DATE_INVALID" };
  }
  if (required === true && value === "") {
    return { code: "VALUE_REQUIRED" };
  }
  const number = numeric(control, value, locale);
  if (number === undefined) {
    return { code: "NUMBER_INVALID" };
  }
  if (control === "date" && value !== "" && !isPlanningDate(value)) {
    return { code: "DATE_INVALID" };
  }
  return { value: number };
}

/** The values of a draft as the contract writes them, and the fields refused before asking. */
function checked(
  fields: readonly FormField[],
  draft: Draft,
  locale: ReturnType<typeof useLocale>,
  badInput: (name: string) => boolean,
): { readonly values: Draft; readonly refused: Map<string, FieldProblem> } {
  const values: Record<string, string> = {};
  const refused = new Map<string, FieldProblem>();
  for (const field of fields) {
    const { name } = field;
    const judgement = judged(field, draft[name] ?? "", locale, badInput(name));
    if ("code" in judgement) {
      refused.set(name, { pointer: `/${name}`, code: judgement.code });
    } else {
      values[name] = judgement.value;
    }
  }
  return { values, refused };
}

/**
 * The refusals of the server by field the form says at a field, by the pointer of each, and the
 * outcome to tell under the form: none when every refusal is said at its field, the refusal without
 * the fields said already otherwise — a refusal by field the form does not show stays in it.
 */
function placed(
  fields: readonly FormField[],
  outcome: Outcome<unknown>,
): { readonly refused: Map<string, FieldProblem>; readonly told: Outcome<unknown> | undefined } {
  const refused = new Map<string, FieldProblem>();
  // A refusal by field is a validation (422), or a value already held (409 `ALREADY_EXISTS`).
  if (!("problem" in outcome) || outcome.problem.fields === undefined) {
    return { refused, told: outcome };
  }
  const rest = outcome.problem.fields.filter((problem) => {
    const field = fields.find(({ name }) => problem.pointer === `/${name}`);
    if (field !== undefined) {
      refused.set(field.name, problem);
    }
    return field === undefined;
  });
  if (refused.size === 0) {
    return { refused, told: outcome };
  }
  return {
    refused,
    told:
      rest.length === 0 ? undefined : { ...outcome, problem: { ...outcome.problem, fields: rest } },
  };
}

/** The fields of a form in their order, those next to one another that share a group gathered. */
function grouped(fields: readonly FormField[]): [FormField, ...FormField[]][] {
  const parts: [FormField, ...FormField[]][] = [];
  for (const field of fields) {
    const last = parts.at(-1);
    if (field.group !== undefined && last?.[0].group === field.group) {
      last.push(field);
    } else {
      parts.push([field]);
    }
  }
  return parts;
}

/** What every control of a field takes: its identity, its value, what describes it, its change. */
interface ControlProps {
  readonly id: string;
  readonly ref: (element: HTMLInputElement | HTMLSelectElement | null) => void;
  readonly value: string;
  readonly "aria-required": true | undefined;
  readonly "aria-invalid": true | undefined;
  readonly "aria-labelledby": string | undefined;
  readonly "aria-describedby": string | undefined;
  readonly onChange: (event: { readonly target: { readonly value: string } }) => void;
}

/**
 * The identifiers of what describes a field, said under it: its note, its refusal, and the object
 * that holds the value it refused as taken; none when nothing does.
 */
function describedBy(
  own: string,
  said: { readonly note: unknown; readonly problem: unknown; readonly holder: unknown },
): string | undefined {
  const described = (["note", "problem", "holder"] as const)
    .filter((part) => said[part] !== undefined)
    .map((part) => `${own}-${part}`);
  return described.length === 0 ? undefined : described.join(" ");
}

/**
 * The control of a field: a choice, its choice of none first; a value shown fixed, read-only, by the
 * text of its choice; a text, a number, a whole number or a date.
 */
function FieldControl({
  control,
  maxLength,
  choices = [],
  none,
  ...props
}: ControlProps & {
  readonly control: FormField["control"];
  readonly maxLength: number | undefined;
  readonly choices: FormField["choices"] | undefined;
  readonly none: string;
}) {
  if (control === "choice") {
    return (
      <NativeSelect {...props}>
        <option value="">{none}</option>
        {choices.map(([option, shown]) => (
          <option key={option} value={option}>
            {shown}
          </option>
        ))}
      </NativeSelect>
    );
  }
  if (control === "fixed") {
    const shown = choices.find(([option]) => option === props.value)?.[1] ?? props.value;
    return <Input {...props} readOnly value={shown} />;
  }
  return (
    <Input
      {...props}
      maxLength={maxLength}
      type={control === "date" ? "date" : undefined}
      inputMode={control === "number" ? "decimal" : control === "whole" ? "numeric" : undefined}
    />
  );
}

/** Render the dialog that creates or modifies an object of the reference data, a project or a sub-project. */
export function ReferenceForm<T = ReferenceObject>({
  title,
  hint,
  creating,
  fields,
  initial,
  ask,
  rules,
  names = {},
  kind,
  target,
  answering,
  onDone,
  onClose,
  onClosed,
}: ReferenceFormProps<T>) {
  const t = useTranslations("reference.form");
  const locale = useLocale();
  const messages = useMessages();
  const list = useListReport();
  const id = useId();
  const [draft, setDraft] = useState(initial);
  const [problems, setProblems] = useState<ReadonlyMap<string, FieldProblem>>(() => new Map());
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const controls = useRef<Partial<Record<string, HTMLInputElement | HTMLSelectElement | null>>>({});
  const open = useRef(true);
  useEffect(() => {
    open.current = true;
    return () => {
      open.current = false;
    };
  }, []);

  /** Say the refusals at their fields, and give the focus to the first one refused. */
  const refuse = (refused: ReadonlyMap<string, FieldProblem>) => {
    setProblems(refused);
    const first = fields.find(({ name }) => refused.has(name));
    if (first !== undefined) {
      controls.current[first.name]?.focus();
    }
  };

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    setOutcome(undefined);
    const { values, refused } = checked(
      fields,
      draft,
      locale,
      (name) => controls.current[name]?.validity.badInput === true,
    );
    // The rules between fields are judged on fields each checked already.
    const broken = refused.size === 0 && rules !== undefined ? rules(values) : refused;
    refuse(broken);
    if (broken.size > 0) {
      return;
    }
    // The reading the form is sent from: a refusal answered once the dialog is gone is told on it.
    const reading = list?.reading ?? "";
    startTransition(async () => {
      const answer = answering(await ask(values).catch(rejected));
      if (answer.kind === "done") {
        onDone(answer.data);
      } else if (!open.current) {
        list?.report({ outcome: answer, reading, names, target });
      } else {
        const told = placed(fields, answer);
        refuse(told.refused);
        setOutcome(told.told);
      }
    });
  };

  /**
   * What holds the value a field refused as already held (`ALREADY_EXISTS`): the object, by its name
   * in the list, or by the label the refusal gives it (`conflicting_object_label`) when the list does
   * not show it — a project, a sub-project (EP-14/L42i) —, or generically; nothing for any other
   * refusal.
   */
  const holderOf = (problem: FieldProblem | undefined) => {
    if (problem?.code !== "ALREADY_EXISTS") {
      return undefined;
    }
    const { conflicting_object_id: holder, conflicting_object_label: label } = problem.params ?? {};
    const name =
      (typeof holder === "string" ? names[holder] : undefined) ??
      (typeof label === "string" && label !== "" ? label : undefined);
    return name === undefined ? t("takenByAnother", { kind }) : t("takenBy", { name });
  };

  /**
   * A field: its label, its control, its note, and its refusal said under it — named after the legend
   * of its group first, when it has one.
   */
  const field = (
    { name, label, control, required, maxLength, choices, none, note, invalid }: FormField,
    legend?: string,
  ) => {
    const problem = problems.get(name);
    const holder = holderOf(problem);
    const own = `${id}-${name}`;
    const props: ControlProps = {
      id: own,
      ref: (element: HTMLInputElement | HTMLSelectElement | null) => {
        controls.current[name] = element;
      },
      value: draft[name] ?? "",
      "aria-labelledby": legend === undefined ? undefined : `${legend} ${own}-label`,
      "aria-required": required === true ? true : undefined,
      "aria-invalid": problem === undefined ? undefined : true,
      "aria-describedby": describedBy(own, { note, problem, holder }),
      onChange: (event: { readonly target: { readonly value: string } }) => {
        setDraft({ ...draft, [name]: event.target.value });
      },
    };
    return (
      <div key={name} className="grid gap-1">
        <Label id={`${own}-label`} htmlFor={own}>
          {label}
        </Label>
        <FieldControl
          {...props}
          control={control}
          maxLength={maxLength}
          choices={choices}
          none={none ?? t("choose")}
        />
        {note === undefined ? null : (
          <p id={`${own}-note`} className="text-xs text-muted-foreground">
            {note}
          </p>
        )}
        {problem === undefined ? null : (
          <p id={`${own}-problem`} className="text-sm text-destructive">
            {problem.code === "NUMBER_INVALID" && invalid !== undefined
              ? invalid
              : problemMessage(problem, { locale, messages })}
          </p>
        )}
        {holder === undefined ? null : (
          <p id={`${own}-holder`} className="text-sm text-destructive">
            {holder}
          </p>
        )}
      </div>
    );
  };

  return (
    <Dialog
      open
      onOpenChange={(opened) => {
        if (!opened) {
          onClose();
        }
      }}
    >
      <DialogContent
        aria-busy={pending}
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          onClosed();
        }}
      >
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>{hint}</DialogDescription>
        </DialogHeader>
        <form aria-label={title} noValidate onSubmit={submit} className="grid gap-3">
          {grouped(fields).map(([first, ...rest]) =>
            first.group === undefined ? (
              field(first)
            ) : (
              <fieldset key={first.name} className="grid gap-1">
                <legend id={`${id}-${first.name}-legend`} className="mb-1 text-sm font-medium">
                  {first.group}
                </legend>
                <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                  {[first, ...rest].map((member) => field(member, `${id}-${first.name}-legend`))}
                </div>
              </fieldset>
            ),
          )}
          <OutcomeNotice
            outcome={outcome}
            onClear={() => {
              setOutcome(undefined);
            }}
            onDismissed={onClose}
          />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>
              <X aria-hidden="true" />
              {t("cancel")}
            </Button>
            <Button type="submit" aria-busy={pending}>
              {creating ? <Plus aria-hidden="true" /> : <Save aria-hidden="true" />}
              {t(pending ? "sending" : creating ? "create" : "save")}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
