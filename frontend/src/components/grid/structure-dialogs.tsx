// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The two dialogs of the gestures of structure of a grid (US-0460): the one that names what a
 * gesture creates — the label of a task, the label, the category and the quantity of a line, which
 * the contract requires of a node created (`NodeCreate`, WF-PLA-0130, WF-DEV-0020) — and the
 * confirmation of the deletion of a summary, which carries its subordinates away (WF-PLA-0070).
 * Neither writes: they hand what was entered to the gesture, which sends it.
 */
"use client";

import { Plus, Trash2, X } from "lucide-react";
import { useLocale, useTranslations } from "next-intl";
import { type RefObject, type SubmitEvent, useId, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NativeSelect } from "@/components/ui/native-select";
import { formatDecimal, parseDecimal } from "@/i18n/format";

import type { Entered, LineCategory } from "./structure-rules";

/** The longest label of a node the contract takes. */
const LABEL_LENGTH = 300;

/** What the dialog of a creation says it creates: a task, or a line under a task. */
export type Created = "task" | "line";

/** The quantity a line starts with. */
const QUANTITY = "1";

/** What is wrong in what a dialog was given, if anything. */
type Problem = "label" | "quantity";

/**
 * The field of the label of a node about to be created: required for a task; optional for a line,
 * which the server names after its task and its role when it is left out (WF-DEV-0020).
 */
function LabelField({
  id,
  created,
  label,
  missing,
  inputRef,
  onChange,
}: {
  readonly id: string;
  readonly created: Created;
  readonly label: string;
  readonly missing: boolean;
  readonly inputRef: RefObject<HTMLInputElement | null>;
  readonly onChange: (label: string) => void;
}) {
  const t = useTranslations("grid.structure");
  const entry = useTranslations("grid.entry");
  const described = missing ? `${id}-problem` : `${id}-composed`;
  return (
    <div className="grid gap-1">
      <Label htmlFor={`${id}-label`}>{t("labelField")}</Label>
      <Input
        ref={inputRef}
        id={`${id}-label`}
        value={label}
        maxLength={LABEL_LENGTH}
        aria-required={created === "task" ? true : undefined}
        aria-invalid={missing ? true : undefined}
        aria-describedby={missing || created === "line" ? described : undefined}
        onChange={(event) => {
          onChange(event.target.value);
        }}
      />
      {created === "line" ? (
        <p id={`${id}-composed`} className="text-xs text-muted-foreground">
          {t("composedLabel")}
        </p>
      ) : null}
      {missing ? (
        <p id={`${id}-problem`} className="text-sm text-destructive">
          {entry("required")}
        </p>
      ) : null}
    </div>
  );
}

/**
 * The dialog that names a node about to be created: its label, and for a line its category and its
 * quantity, read in the format of the language. Hands what was entered when it is valid.
 */
export function CreateForm({
  created,
  title,
  under,
  categories,
  pending,
  onCreate,
  onCancel,
}: {
  readonly created: Created;
  /** What the dialog is titled: the gesture, with the row it acts on. */
  readonly title: string;
  /** The row the dialog acts on, named; none for the first task of a grid with no row. */
  readonly under: string | undefined;
  /** The categories a line is created from, the active ones. */
  readonly categories: readonly LineCategory[];
  readonly pending: boolean;
  readonly onCreate: (entered: Entered) => void;
  readonly onCancel: () => void;
}) {
  const t = useTranslations("grid.structure");
  const entry = useTranslations("grid.entry");
  const form = useTranslations("reference.form");
  const locale = useLocale();
  const id = useId();
  const active = categories.filter((category) => category.active);
  const [label, setLabel] = useState("");
  const [category, setCategory] = useState(active[0]?.id ?? "");
  const [quantity, setQuantity] = useState(formatDecimal(QUANTITY, locale));
  const [problem, setProblem] = useState<Problem>();
  const labelInput = useRef<HTMLInputElement>(null);
  const quantityInput = useRef<HTMLInputElement>(null);
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    const typed = label.trim();
    // The label of a line is optional: left out, the server composes it of the task and the role.
    if (typed === "" && created === "task") {
      setProblem("label");
      labelInput.current?.focus();
      return;
    }
    if (created === "task") {
      setProblem(undefined);
      onCreate({ label: typed, line: undefined });
      return;
    }
    const parsed = parseDecimal(quantity, locale, "decimal");
    if (parsed === undefined) {
      setProblem("quantity");
      quantityInput.current?.focus();
      return;
    }
    setProblem(undefined);
    onCreate({ label: typed, line: { category, quantity: parsed } });
  };
  const hint = t(created === "task" ? "taskHint" : "lineHint");
  return (
    <>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription>
          {under === undefined ? hint : t("underHint", { under, hint })}
        </DialogDescription>
      </DialogHeader>
      <form aria-label={title} noValidate onSubmit={submit} className="grid gap-3">
        <LabelField
          id={id}
          created={created}
          label={label}
          missing={problem === "label"}
          inputRef={labelInput}
          onChange={setLabel}
        />
        {created === "line" ? (
          <>
            <div className="grid gap-1">
              <Label htmlFor={`${id}-category`}>{t("categoryField")}</Label>
              <NativeSelect
                id={`${id}-category`}
                value={category}
                onChange={(event) => {
                  setCategory(event.target.value);
                }}
              >
                {active.map((choice) => (
                  <option key={choice.id} value={choice.id}>
                    {choice.label}
                  </option>
                ))}
              </NativeSelect>
            </div>
            <div className="grid gap-1">
              <Label htmlFor={`${id}-quantity`}>{t("quantityField")}</Label>
              <Input
                ref={quantityInput}
                id={`${id}-quantity`}
                inputMode="decimal"
                value={quantity}
                aria-required
                aria-invalid={problem === "quantity" ? true : undefined}
                aria-describedby={problem === "quantity" ? `${id}-problem` : undefined}
                onChange={(event) => {
                  setQuantity(event.target.value);
                }}
              />
              {problem === "quantity" ? (
                <p id={`${id}-problem`} className="text-sm text-destructive">
                  {entry("notANumber", { example: formatDecimal("1234.5", locale) })}
                </p>
              ) : null}
            </div>
          </>
        ) : null}
        <DialogFooter>
          <Button type="button" variant="outline" onClick={onCancel}>
            <X aria-hidden="true" />
            {form("cancel")}
          </Button>
          <Button type="submit" aria-busy={pending}>
            <Plus aria-hidden="true" />
            {form(pending ? "sending" : "create")}
          </Button>
        </DialogFooter>
      </form>
    </>
  );
}

/**
 * The confirmation of the deletion of a node that carries others away: a summary, whose
 * subordinates, their lines and their links go with it (WF-PLA-0070).
 */
export function DeleteConfirmation({
  label,
  pending,
  onConfirm,
  onCancel,
}: {
  readonly label: string;
  readonly pending: boolean;
  readonly onConfirm: () => void;
  readonly onCancel: () => void;
}) {
  const t = useTranslations("grid.structure");
  const form = useTranslations("reference.form");
  return (
    <>
      <DialogHeader>
        <DialogTitle>{t("deleteTitle", { label })}</DialogTitle>
        <DialogDescription>{t("deleteHint", { label })}</DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          <X aria-hidden="true" />
          {form("cancel")}
        </Button>
        <Button type="button" aria-busy={pending} onClick={onConfirm}>
          <Trash2 aria-hidden="true" />
          {t(pending ? "deleting" : "deleteConfirm")}
        </Button>
      </DialogFooter>
    </>
  );
}
