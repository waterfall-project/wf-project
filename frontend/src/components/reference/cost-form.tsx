// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The form that creates or modifies a nature (WF-REF-0030) or a category of cost (WF-REF-0040), in a
 * dialog over the settings of the costs (EP-02/L43a): a nature by its code, its name and its type,
 * offered among the three of the contract — its modification says that the type no longer changes
 * once a category attached to it is employed, as the contract does (`CostTypeKind`,
 * `updateCostType`); a category by its code, its name, its nature — chosen among the active ones, a
 * deactivated one being no longer offered to an entry (WF-REF-0010), save the one the category is
 * attached to, marked deactivated — and its accounting code, which may stay empty.
 *
 * The form is checked here before anything is asked: a field required left empty is said at the
 * field, which takes the focus — a category without a nature is refused so (WF-REF-0040). The rest is
 * the server's to judge: a refusal by field (422, `fields[]`, convention #293) is said at each field
 * it points at, by the sentence of its code and its parameters (`problemMessage`), the first field
 * refused taking the focus; any other refusal — the code of a nature already taken, the type of a
 * nature whose category is employed (409), the version stale (412) with the offer to read the page
 * anew, the API out of reach, a field the form does not show — is told under the form
 * (`OutcomeNotice`), which stays open to be corrected.
 *
 * The button that sends says the write under way. The dialog may be closed meanwhile: the answer of
 * the server is handed back all the same (`onDone`), and a refusal is told above the list, on the
 * reading the form was sent from (`useListReport`) — what the server did is never left unsaid.
 */
"use client";

import { Plus, Save, X } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import {
  type ReactNode,
  type SubmitEvent,
  useEffect,
  useId,
  useRef,
  useState,
  useTransition,
} from "react";

import { createCostObject, updateCostObject } from "@/api/actions/reference";
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
import { problemMessage } from "@/i18n/problem";

import {
  COST_TYPE_KIND_VALUES,
  type CostObject,
  idOf,
  isCostTypeKind,
  type NatureChoice,
} from "./cost-kinds";
import { useListReport } from "./reactivation";

/** A refusal of one field, by the server or by the form. */
type FieldProblem = components["schemas"]["FieldProblem"];

/** A field of the form, by the name the contract gives it in the body of the write. */
type Field = "code" | "label" | "kind" | "cost_type_id" | "accounting_code";

/** What the form holds, as typed. */
type Draft = Readonly<Record<Field, string>>;

/** The fields of each kind of object, in the order of the form: the first refused takes the focus. */
const FIELDS = {
  cost_type: ["code", "label", "kind"],
  cost_category: ["code", "label", "cost_type_id", "accounting_code"],
} as const satisfies Readonly<Record<string, readonly Field[]>>;

/** The fields a write requires, which the form refuses empty before asking anything. */
const REQUIRED: ReadonlySet<Field> = new Set(["code", "label", "kind", "cost_type_id"]);

/** The longest each text the contract takes; none for the choices nor the accounting code. */
const MAX_LENGTH: Partial<Record<Field, number>> = { code: 20, label: 200 };

/** What the form creates or modifies. */
export interface CostFormProps {
  readonly kind: keyof typeof FIELDS;
  /** The object modified, as its row shows it; none for a creation. */
  readonly row: CostObject | undefined;
  /** The natures a category may be attached to, in the order of the server. */
  readonly natures: readonly NatureChoice[];
  /** Take the answer of the server, the dialog open or closed. */
  readonly onDone: (answer: CostObject) => void;
  readonly onClose: () => void;
  /** Give the focus back where the dialog was opened from, once it has closed. */
  readonly onClosed: () => void;
}

/** What the form starts from: the object modified, or nothing typed. */
function draftOf(row: CostObject | undefined): Draft {
  const empty = { code: "", label: "", kind: "", cost_type_id: "", accounting_code: "" };
  if (row === undefined) {
    return empty;
  }
  return "cost_category_id" in row
    ? {
        ...empty,
        code: row.code,
        label: row.label,
        cost_type_id: row.cost_type_id,
        accounting_code: row.accounting_code ?? "",
      }
    : { ...empty, code: row.code, label: row.label, kind: row.kind };
}

/** The fields required left empty, each refused as the server would refuse it. */
function missing(kind: CostFormProps["kind"], draft: Draft): Map<Field, FieldProblem> {
  const fields: readonly Field[] = FIELDS[kind];
  return new Map(
    fields
      .filter((field) => REQUIRED.has(field) && draft[field].trim() === "")
      .map((field) => [field, { pointer: `/${field}`, code: "VALUE_REQUIRED" }]),
  );
}

/**
 * The refusals of the server by field the form says at a field, by the pointer of each (`/code`), and
 * the outcome to tell under the form: none when every refusal is said at its field, the refusal
 * without the fields said already otherwise — a refusal by field the form does not show stays in it.
 */
function placed(
  kind: CostFormProps["kind"],
  outcome: Outcome<unknown>,
): { readonly fields: Map<Field, FieldProblem>; readonly told: Outcome<unknown> | undefined } {
  const fields = new Map<Field, FieldProblem>();
  if (outcome.kind !== "refused" || outcome.problem.fields === undefined) {
    return { fields, told: outcome };
  }
  const own: readonly Field[] = FIELDS[kind];
  const rest = outcome.problem.fields.filter((problem) => {
    const field = own.find((each) => problem.pointer === `/${each}`);
    if (field !== undefined) {
      fields.set(field, problem);
    }
    return field === undefined;
  });
  if (fields.size === 0) {
    return { fields, told: outcome };
  }
  return {
    fields,
    told:
      rest.length === 0 ? undefined : { ...outcome, problem: { ...outcome.problem, fields: rest } },
  };
}

/** The write the form asks, from what it holds: its texts trimmed, an empty accounting code none. */
function writeOf(kind: CostFormProps["kind"], draft: Draft) {
  const code = draft.code.trim();
  const label = draft.label.trim();
  if (kind === "cost_type") {
    const type = draft.kind;
    if (!isCostTypeKind(type)) {
      // The type is chosen among those of the contract, and checked before anything is asked.
      throw new Error("a nature is written with a type of the contract");
    }
    return { kind, body: { code, label, kind: type } } as const;
  }
  const accounting = draft.accounting_code.trim();
  return {
    kind,
    body: {
      code,
      label,
      cost_type_id: draft.cost_type_id,
      accounting_code: accounting === "" ? null : accounting,
    },
  } as const;
}

/** Ask the server to create the object, or to modify it from the version read. */
function ask(kind: CostFormProps["kind"], draft: Draft, row: CostObject | undefined) {
  const write = writeOf(kind, draft);
  if (row === undefined) {
    return createCostObject(write);
  }
  const lock = { lock_version: row.lock_version };
  return write.kind === "cost_type"
    ? updateCostObject(idOf(row), { kind: write.kind, body: { ...write.body, ...lock } })
    : updateCostObject(idOf(row), { kind: write.kind, body: { ...write.body, ...lock } });
}

/** A field of the form: its label, its control, and its refusal said under it. */
function FormField({
  id,
  label,
  problem,
  children,
}: {
  readonly id: string;
  readonly label: string;
  readonly problem: string | undefined;
  readonly children: ReactNode;
}) {
  return (
    <div className="grid gap-1">
      <Label htmlFor={id}>{label}</Label>
      {children}
      {problem === undefined ? null : (
        <p id={`${id}-problem`} className="text-sm text-destructive">
          {problem}
        </p>
      )}
    </div>
  );
}

/** A nature offered to a category, and whether it is deactivated — the one it is attached to. */
interface Offered {
  readonly id: string;
  readonly code: string | undefined;
  readonly label: string;
  readonly deactivated: boolean;
}

/**
 * The natures offered to a category: the active ones, and the one it is attached to, marked
 * deactivated when it is no longer among them — by its code when the page read it.
 */
function offeredNatures(natures: readonly NatureChoice[], row: CostObject | undefined): Offered[] {
  const offered = natures
    .filter((nature) => nature.active)
    .map((nature) => ({ ...nature, deactivated: false }));
  if (row === undefined || !("cost_category_id" in row)) {
    return offered;
  }
  if (offered.some((nature) => nature.id === row.cost_type_id)) {
    return offered;
  }
  const read = natures.find((nature) => nature.id === row.cost_type_id);
  return [
    ...offered,
    { id: row.cost_type_id, code: read?.code, label: row.cost_type_label, deactivated: true },
  ];
}

/** Render the dialog that creates or modifies a nature or a category of cost. */
export function CostForm({ kind, row, natures, onDone, onClose, onClosed }: CostFormProps) {
  const t = useTranslations("reference");
  const columns = useTranslations("grid.columns");
  const kinds = useTranslations("enums.CostTypeKind");
  const locale = useLocale();
  const messages = useMessages();
  const list = useListReport();
  const id = useId();
  const [draft, setDraft] = useState(() => draftOf(row));
  const [problems, setProblems] = useState<ReadonlyMap<Field, FieldProblem>>(() => new Map());
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const controls = useRef<Partial<Record<Field, HTMLInputElement | HTMLSelectElement | null>>>({});
  const open = useRef(true);
  useEffect(() => {
    open.current = true;
    return () => {
      open.current = false;
    };
  }, []);

  /** Say the refusals at their fields, and give the focus to the first one refused. */
  const refuse = (refused: ReadonlyMap<Field, FieldProblem>) => {
    setProblems(refused);
    const first = FIELDS[kind].find((field) => refused.has(field));
    if (first !== undefined) {
      controls.current[first]?.focus();
    }
  };

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    setOutcome(undefined);
    const empty = missing(kind, draft);
    refuse(empty);
    if (empty.size > 0) {
      return;
    }
    // The reading the form is sent from: a refusal answered once the dialog is gone is told on it.
    const reading = list?.reading ?? "";
    startTransition(async () => {
      const answer = await ask(kind, draft, row).catch(rejected);
      if (answer.kind === "done") {
        onDone(answer.data);
      } else if (!open.current) {
        list?.report({
          outcome: answer,
          reading,
          names: {},
          target: row === undefined ? undefined : `modify ${idOf(row)}`,
        });
      } else {
        const { fields, told } = placed(kind, answer);
        refuse(fields);
        setOutcome(told);
      }
    });
  };

  /** What a control of a field carries: its identifier, its value, and its refusal. */
  const control = (field: Field) => {
    const problem = problems.get(field);
    return {
      id: `${id}-${field}`,
      ref: (element: HTMLInputElement | HTMLSelectElement | null) => {
        controls.current[field] = element;
      },
      value: draft[field],
      "aria-required": REQUIRED.has(field) ? true : undefined,
      "aria-invalid": problem === undefined ? undefined : true,
      "aria-describedby": problem === undefined ? undefined : `${id}-${field}-problem`,
      onChange: (event: { readonly target: { readonly value: string } }) => {
        setDraft({ ...draft, [field]: event.target.value });
      },
    };
  };
  const said = (field: Field) => {
    const problem = problems.get(field);
    return problem === undefined ? undefined : problemMessage(problem, { locale, messages });
  };
  const text = (field: Field, label: string) => (
    <FormField id={`${id}-${field}`} label={label} problem={said(field)}>
      <Input {...control(field)} maxLength={MAX_LENGTH[field]} />
    </FormField>
  );
  const choice = (field: Field, label: string, options: readonly (readonly [string, string])[]) => (
    <FormField id={`${id}-${field}`} label={label} problem={said(field)}>
      <NativeSelect {...control(field)}>
        <option value="">{t("costForm.choose")}</option>
        {options.map(([value, shown]) => (
          <option key={value} value={value}>
            {shown}
          </option>
        ))}
      </NativeSelect>
    </FormField>
  );
  const natureText = (nature: Offered) => {
    const named =
      nature.code === undefined
        ? nature.label
        : t("codedChoice", { code: nature.code, label: nature.label });
    return nature.deactivated ? t("costForm.deactivatedChoice", { choice: named }) : named;
  };

  const title =
    row === undefined
      ? t(kind === "cost_type" ? "costForm.createCostType" : "costForm.createCostCategory")
      : t("costForm.modify", { name: row.label });
  const hint =
    kind === "cost_category"
      ? "costForm.costCategoryHint"
      : row === undefined
        ? "costForm.costTypeHint"
        : "costForm.costTypeModifyHint";
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
          <DialogDescription>{t(hint)}</DialogDescription>
        </DialogHeader>
        <form aria-label={title} noValidate onSubmit={submit} className="grid gap-3">
          {text("code", columns("code"))}
          {text("label", columns("label"))}
          {kind === "cost_type"
            ? choice(
                "kind",
                columns("costTypeKind"),
                COST_TYPE_KIND_VALUES.map((value) => [value, kinds(value)] as const),
              )
            : choice(
                "cost_type_id",
                columns("costType"),
                offeredNatures(natures, row).map(
                  (nature) => [nature.id, natureText(nature)] as const,
                ),
              )}
          {kind === "cost_category" ? text("accounting_code", columns("accountingCode")) : null}
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
              {t("costForm.cancel")}
            </Button>
            <Button type="submit" aria-busy={pending}>
              {row === undefined ? <Plus aria-hidden="true" /> : <Save aria-hidden="true" />}
              {t(
                pending
                  ? "costForm.sending"
                  : row === undefined
                    ? "costForm.create"
                    : "costForm.save",
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
