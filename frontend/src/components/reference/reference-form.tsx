// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The form that creates or modifies an object of the reference data, in a dialog over its list
 * (EP-02/L43): the fields of its kind, each by the pointer of the contract it writes (`code`,
 * `capacity/monthly_hours`), a text, a number or a choice.
 *
 * The form is checked here before anything is asked: a field required left empty, a number that is
 * not one in the language of the reader (`parseDecimal`), is said at the field, which takes the
 * focus. The rest is the server's to judge: a refusal by field (422, `fields[]`, convention #293) is
 * said at each field it points at, by the sentence of its code and its parameters
 * (`problemMessage`), the first field refused taking the focus; any other refusal — a code already
 * taken (409), the version stale (412) with the offer to read the page anew, the API out of reach, a
 * field the form does not show — is told under the form (`OutcomeNotice`), which stays open to be
 * corrected, without what is said at the fields already.
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
import { OutcomeNotice } from "@/components/commands/outcome-notice";
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
import { parseDecimal } from "@/i18n/format";
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
  readonly control: "text" | "number" | "choice";
  readonly required?: boolean;
  /** The longest text the contract takes. */
  readonly maxLength?: number;
  /** The values a choice offers, each with its text, in their order. */
  readonly choices?: readonly (readonly [string, string])[];
  /** The text of the choice of none — a root for the parent of a node —; « Choose… » otherwise. */
  readonly none?: string;
}

/** A field of text the form requires, no longer than the contract takes. */
export function required(name: string, label: string, maxLength: number): FormField {
  return { name, label, control: "text", required: true, maxLength };
}

/** What a form holds, by the name of each field. */
export type Draft = Readonly<Record<string, string>>;

/** What a form of the reference data writes, and how. */
export interface ReferenceFormProps extends Omit<ListForm, "row"> {
  readonly title: string;
  readonly hint: string;
  /** Whether the form creates an object rather than modifies one. */
  readonly creating: boolean;
  readonly fields: readonly FormField[];
  /** What the form starts from: the object modified, or nothing typed. */
  readonly initial: Draft;
  /**
   * Ask the server, from the values checked: a text trimmed, a number as the contract writes it, a
   * choice as chosen — none an empty text.
   */
  readonly ask: (values: Draft) => Promise<Outcome<ReferenceObject>>;
}

/** The values of a draft as the contract writes them, and the fields refused before asking. */
function checked(
  fields: readonly FormField[],
  draft: Draft,
  locale: ReturnType<typeof useLocale>,
): { readonly values: Draft; readonly refused: Map<string, FieldProblem> } {
  const values: Record<string, string> = {};
  const refused = new Map<string, FieldProblem>();
  for (const { name, control, required } of fields) {
    const typed = draft[name] ?? "";
    const value = control === "choice" ? typed : typed.trim();
    const number = control === "number" && value !== "" ? parseDecimal(value, locale) : value;
    if (required === true && value === "") {
      refused.set(name, { pointer: `/${name}`, code: "VALUE_REQUIRED" });
    } else if (number === undefined) {
      refused.set(name, { pointer: `/${name}`, code: "NUMBER_INVALID" });
    } else {
      values[name] = number;
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
  if (outcome.kind !== "refused" || outcome.problem.fields === undefined) {
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

/** Render the dialog that creates or modifies an object of the reference data. */
export function ReferenceForm({
  title,
  hint,
  creating,
  fields,
  initial,
  ask,
  target,
  answering,
  onDone,
  onClose,
  onClosed,
}: ReferenceFormProps) {
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
    const { values, refused } = checked(fields, draft, locale);
    refuse(refused);
    if (refused.size > 0) {
      return;
    }
    // The reading the form is sent from: a refusal answered once the dialog is gone is told on it.
    const reading = list?.reading ?? "";
    startTransition(async () => {
      const answer = answering(await ask(values).catch(rejected));
      if (answer.kind === "done") {
        onDone(answer.data);
      } else if (!open.current) {
        list?.report({ outcome: answer, reading, names: {}, target });
      } else {
        const told = placed(fields, answer);
        refuse(told.refused);
        setOutcome(told.told);
      }
    });
  };

  /** A field: its label, its control, and its refusal said under it. */
  const field = ({ name, label, control, required, maxLength, choices, none }: FormField) => {
    const problem = problems.get(name);
    const own = `${id}-${name}`;
    const props = {
      id: own,
      ref: (element: HTMLInputElement | HTMLSelectElement | null) => {
        controls.current[name] = element;
      },
      value: draft[name] ?? "",
      "aria-required": required === true ? true : undefined,
      "aria-invalid": problem === undefined ? undefined : true,
      "aria-describedby": problem === undefined ? undefined : `${own}-problem`,
      onChange: (event: { readonly target: { readonly value: string } }) => {
        setDraft({ ...draft, [name]: event.target.value });
      },
    };
    return (
      <div key={name} className="grid gap-1">
        <Label htmlFor={own}>{label}</Label>
        {control === "choice" ? (
          <NativeSelect {...props}>
            <option value="">{none ?? t("choose")}</option>
            {(choices ?? []).map(([value, shown]) => (
              <option key={value} value={value}>
                {shown}
              </option>
            ))}
          </NativeSelect>
        ) : (
          <Input
            {...props}
            maxLength={maxLength}
            inputMode={control === "number" ? "decimal" : undefined}
          />
        )}
        {problem === undefined ? null : (
          <p id={`${own}-problem`} className="text-sm text-destructive">
            {problemMessage(problem, { locale, messages })}
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
          {fields.map(field)}
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
