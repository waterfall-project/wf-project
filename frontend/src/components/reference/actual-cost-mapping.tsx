// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The correspondence of the extraction of the actual costs (FBS-3.1.3, WF-REF-0190, US-0620): for
 * each of the five columns Waterfall reads, the labels under which the ERP names it, and the labels
 * of the columns it keeps for information, declared one by one. A bar says the columns required
 * that have no label, as the server computes them (`is_complete`, `missing_columns`): the front
 * computes nothing of it, and takes it from the answer of a write as it takes it from the
 * reading.
 *
 * A session that holds `cost_settings.write` adds, modifies and removes a label, and declares and
 * removes a kept column, in one form that replaces the correspondence whole with the version read
 * (`setActualCostMapping`); another reads the lists, with no command. The server alone judges the
 * labels: each list stops at the ceiling of the contract (`KEPT_COLUMNS_LIMIT` for the kept
 * columns, `LABELS_LIMIT` for a column read), the refusal of the list itself (`/kept_columns` or
 * `/columns/<rank>/labels`, `VALUE_TOO_LONG`) being said under it; a refusal by
 * field (422) is said at the label its pointer designates (`/columns/<rank>/labels/<rank>`,
 * `/kept_columns/<rank>`), the first one refused taking the focus, a duplicate
 * (`DUPLICATE_COLUMN_LABEL`) naming the label it doubles (`params.duplicate_of`); any other
 * refusal is told under the form — the version stale (412) with the offer to read the page anew,
 * whose reading takes the place of the draft when it has not changed since it was sent, the form
 * never mounted again by a `key`: it keeps the focus and what is typed while the reading arrives.
 * A reading strictly newer than the answer, with nothing typed since the send, replaces the draft
 * and may take the focus: this is intended (#2266). The fields are held while the write is under
 * way and lose the focus: with any answer that refuses no label, it goes back to the control that
 * held it. The answer takes the place of the reading while it is newer (`lock_version`).
 */
"use client";

import { Columns3, Plus, Save, Trash2, TableProperties } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState } from "react";

import { setActualCostMapping } from "@/api/actions/reference";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { useHeldCommand } from "@/components/commands/held";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { OutcomeNotice, useNoteRefusal, useReadAnew } from "@/components/commands/outcome-notice";
import { SectionCard } from "@/components/shell/section-card";
import { useSaid } from "@/components/notices/said";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { problemMessage } from "@/i18n/problem";

type Mapping = components["schemas"]["ActualCostMapping"];
type Source = components["schemas"]["ActualCostSourceColumn"];
type FieldProblem = components["schemas"]["FieldProblem"];

/**
 * The width a field of a label is bounded to, so that a line stays readable in a card as wide as
 * the screen (EP-25, US-2110): a label is a few words, never a paragraph.
 */
const READING_WIDTH = "max-w-xl";

/** The longest label the contract takes. */
const LABEL_LENGTH = 200;

/**
 * The most kept columns the contract takes: the `maxItems` of `kept_columns` in
 * `ActualCostMappingWrite` (`docs/api/components/schemas/reference.yaml`), which the generated
 * client does not carry; `actual-cost-mapping.dom.test.tsx` proves it equal to the schema.
 */
export const KEPT_COLUMNS_LIMIT = 50;

/**
 * The most labels the contract takes for a column read: the `maxItems` of `labels` in
 * `ActualCostMappingColumnWrite`, which the generated client does not carry;
 * `actual-cost-mapping.dom.test.tsx` proves it equal to the schema.
 */
export const LABELS_LIMIT = 20;

/**
 * A label being typed, with a key of its own that keeps it through the removal of the ones
 * before.
 */
interface Row {
  readonly key: number;
  readonly text: string;
}

/** A list of labels: the rank of a column read, or the kept columns. */
type Scope = number | "kept";

/** The most a list of labels takes: the kept columns, or the labels of a column read. */
function limitOf(scope: Scope): number {
  return scope === "kept" ? KEPT_COLUMNS_LIMIT : LABELS_LIMIT;
}

/**
 * What the form holds: the labels of each column read, in the order of the contract, and the kept
 * ones.
 */
interface Draft {
  readonly next: number;
  readonly columns: readonly {
    readonly column: Source;
    readonly required: boolean;
    readonly rows: readonly Row[];
  }[];
  readonly kept: readonly Row[];
}

/** The rows of some labels, numbered from a key. */
function rowsOf(texts: readonly string[], from: number): Row[] {
  return texts.map((text, rank) => ({ key: from + rank, text }));
}

/** The form's start: the correspondence as it is read. */
function draftOf({ columns, kept_columns: kept }: Mapping): Draft {
  let next = 0;
  const take = (texts: readonly string[]) => {
    const rows = rowsOf(texts, next);
    next += rows.length;
    return rows;
  };
  const read = columns.map(({ column, required, labels }) => ({
    column,
    required,
    rows: take(labels),
  }));
  const keptRows = take(kept);
  return { next, columns: read, kept: keptRows };
}

/** A list of the draft changed, the key a new row takes numbered from the draft's. */
function changed(
  draft: Draft,
  scope: Scope,
  change: (rows: readonly Row[], next: number) => readonly Row[],
  added = 0,
): Draft {
  const next = draft.next + added;
  return scope === "kept"
    ? { ...draft, next, kept: change(draft.kept, draft.next) }
    : {
        ...draft,
        next,
        columns: draft.columns.map((each, rank) =>
          rank === scope ? { ...each, rows: change(each.rows, draft.next) } : each,
        ),
      };
}

/** The pointer of the label of a list at a rank, as the contract designates it. */
function pointer(scope: Scope, rank: number): string {
  return scope === "kept"
    ? `/kept_columns/${String(rank)}`
    : `/columns/${String(scope)}/labels/${String(rank)}`;
}

/** The labels of a draft, trimmed, as the contract takes them: the correspondence whole. */
function written(
  draft: Draft,
  lockVersion: number,
): components["schemas"]["ActualCostMappingWrite"] {
  const texts = (rows: readonly Row[]) => rows.map(({ text }) => text.trim());
  return {
    columns: draft.columns.map(({ column, rows }) => ({ column, labels: texts(rows) })),
    kept_columns: texts(draft.kept),
    lock_version: lockVersion,
  };
}

/**
 * The list of labels of a pointer of a write: the label it designates, and the column it belongs
 * to.
 */
function labelAt(
  sent: components["schemas"]["ActualCostMappingWrite"],
  at: unknown,
): { readonly label: string; readonly column: Source | undefined } | undefined {
  const [, list, rank, , label] = typeof at === "string" ? at.split("/") : [];
  if (list === "kept_columns") {
    const text = sent.kept_columns[Number(rank)];
    return text === undefined ? undefined : { label: text, column: undefined };
  }
  const column = sent.columns[Number(rank)];
  const text = column?.labels[Number(label)];
  return column === undefined || text === undefined
    ? undefined
    : { label: text, column: column.column };
}

/** The bar of the columns required that have no label, or the word that none lacks. */
function RequiredBar({ mapping }: { readonly mapping: Mapping }) {
  const t = useTranslations("reference.actualCostMapping");
  const column = useTranslations("enums.ActualCostSourceColumn");
  return (
    <p
      role="status"
      aria-live="polite"
      className={
        mapping.is_complete
          ? "text-sm text-muted-foreground"
          : "text-sm font-medium text-destructive"
      }
    >
      {mapping.is_complete
        ? t("complete")
        : t("missing", {
            count: mapping.missing_columns.length,
            columns: mapping.missing_columns.map((each) => column(each)).join(", "),
          })}
    </p>
  );
}

/** What a session that does not write reads of a list: its labels, or the word that it has none. */
function ReadList({ labels, none }: { readonly labels: readonly string[]; readonly none: string }) {
  return labels.length === 0 ? (
    <p className="text-sm text-muted-foreground">{none}</p>
  ) : (
    <ul className="list-disc pl-5 text-sm">
      {labels.map((label, rank) => (
        <li key={`${String(rank)}-${label}`}>{label}</li>
      ))}
    </ul>
  );
}

/** The correspondence, read: a session that may read the cost settings but not modify them. */
function ReadMapping({ mapping }: { readonly mapping: Mapping }) {
  const t = useTranslations("reference.actualCostMapping");
  const column = useTranslations("enums.ActualCostSourceColumn");
  return (
    <>
      <SectionCard title={t("readColumns")} icon={Columns3}>
        <div className="grid gap-4">
          {mapping.columns.map((each) => (
            <section key={each.column} aria-label={column(each.column)} className="grid gap-1">
              <h3 className="text-sm font-semibold">
                {column(each.column)}{" "}
                <span className="font-normal text-muted-foreground">
                  {each.required ? t("required") : t("optional")}
                </span>
              </h3>
              <ReadList labels={each.labels} none={t("noLabel")} />
            </section>
          ))}
        </div>
      </SectionCard>
      <SectionCard title={t("kept")} icon={TableProperties}>
        <ReadList labels={mapping.kept_columns} none={t("noKept")} />
      </SectionCard>
    </>
  );
}

/** What the rows of a list need of the form that holds them. */
interface ListProps {
  readonly scope: Scope;
  readonly rows: readonly Row[];
  /** The name of the list the label of a row and its commands carry. */
  readonly name: string;
  readonly problems: ReadonlyMap<number, FieldProblem>;
  readonly sent: components["schemas"]["ActualCostMappingWrite"] | undefined;
  readonly register: (id: string, element: HTMLElement | null) => void;
  readonly update: (change: (draft: Draft) => Draft, focus: string, removed?: number) => void;
  readonly retype: (scope: Scope, key: number, text: string) => void;
  /** The refusal of this list as a whole, said under it: the list too long. */
  readonly listProblem?: FieldProblem | undefined;
}

/** The sentence that says what a refusal of a label is, and which label it doubles. */
function RowProblem({
  id,
  problem,
  sent,
}: {
  readonly id: string;
  readonly problem: FieldProblem;
  readonly sent: ListProps["sent"];
}) {
  const t = useTranslations("reference.actualCostMapping");
  const column = useTranslations("enums.ActualCostSourceColumn");
  const locale = useLocale();
  const messages = useMessages();
  const doubled =
    problem.code === "DUPLICATE_COLUMN_LABEL" && sent !== undefined
      ? labelAt(sent, problem.params?.duplicate_of)
      : undefined;
  return (
    <p id={id} className="text-sm text-destructive">
      {problemMessage(problem, { locale, messages })}
      {doubled === undefined
        ? null
        : " " +
          (doubled.column === undefined
            ? t("doublesKept", { label: doubled.label })
            : t("doubles", { label: doubled.label, column: column(doubled.column) }))}
    </p>
  );
}

/** A list of labels with its commands: a field and a removal for each, and the addition of one. */
function LabelList({
  scope,
  rows,
  name,
  problems,
  sent,
  register,
  update,
  retype,
  listProblem,
}: ListProps) {
  const t = useTranslations("reference.actualCostMapping");
  const commands = useTranslations("commands");
  const id = useId();
  const kept = scope === "kept";
  // The ceiling of the contract: the command that adds one more is unavailable at it, its
  // condition said beside it.
  const limit = limitOf(scope);
  const full = rows.length >= limit;
  const fullText = kept
    ? t("keptFull", { max: limit })
    : t("labelsFull", { max: limit, column: name });
  const fullId = `${id}-full`;
  return (
    <div className="grid gap-2">
      <ul
        className="grid gap-2"
        aria-describedby={listProblem === undefined ? undefined : `${id}-list-problem`}
      >
        {rows.map(({ key, text }, rank) => {
          const problem = problems.get(key);
          const own = `${id}-${String(key)}`;
          const label = kept
            ? t("keptLabel", { n: rank + 1 })
            : t("label", { n: rank + 1, column: name });
          const remove = kept
            ? t("removeKept", { n: rank + 1 })
            : t("remove", { n: rank + 1, column: name });
          return (
            <li key={key} className="grid gap-1">
              <div className="flex items-center gap-2">
                <Input
                  id={own}
                  className={READING_WIDTH}
                  ref={(element) => {
                    register(`row-${String(key)}`, element);
                  }}
                  aria-label={label}
                  aria-invalid={problem === undefined ? undefined : true}
                  aria-describedby={problem === undefined ? undefined : `${own}-problem`}
                  maxLength={LABEL_LENGTH}
                  value={text}
                  onChange={(event) => {
                    retype(scope, key, event.target.value);
                  }}
                />
                <CommandTooltip label={remove} help={commands("removeMappingLabel.help")}>
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    aria-label={remove}
                    onClick={() => {
                      update(
                        (draft) =>
                          changed(draft, scope, (before) =>
                            before.filter((row) => row.key !== key),
                          ),
                        `add-${String(scope)}`,
                        key,
                      );
                    }}
                  >
                    <Trash2 aria-hidden="true" />
                  </Button>
                </CommandTooltip>
              </div>
              {problem === undefined ? null : (
                <RowProblem id={`${own}-problem`} problem={problem} sent={sent} />
              )}
            </li>
          );
        })}
      </ul>
      {listProblem === undefined ? null : (
        <p id={`${id}-list-problem`} className="text-sm text-destructive">
          {kept
            ? t("keptTooMany", { max: maxOf(listProblem, limit) })
            : t("labelsTooMany", { max: maxOf(listProblem, limit), column: name })}
        </p>
      )}
      {full ? (
        <p id={fullId} className="text-sm text-muted-foreground">
          {fullText}
        </p>
      ) : null}
      <div>
        <CommandTooltip
          label={kept ? t("addKept") : t("add", { column: name })}
          help={commands("addMappingLabel.help")}
          unavailable={full ? fullText : undefined}
          describedBy={full ? fullId : undefined}
        >
          <Button
            type="button"
            variant="outline"
            size="sm"
            ref={(element) => {
              register(`add-${String(scope)}`, element);
            }}
            aria-label={kept ? t("addKept") : t("add", { column: name })}
            onClick={() => {
              // Unavailable at the ceiling: the press adds nothing.
              if (full) {
                return;
              }
              update(
                (draft) =>
                  changed(draft, scope, (before, next) => [...before, { key: next, text: "" }], 1),
                `row-new`,
              );
            }}
          >
            <Plus aria-hidden="true" />
            {kept ? t("addKept") : t("addShort")}
          </Button>
        </CommandTooltip>
      </div>
    </div>
  );
}

/** The ceiling the server names in a refusal of the list, the contract's when it names none. */
function maxOf(problem: FieldProblem, contract: number): number {
  const max = problem.params?.max_length;
  return typeof max === "number" ? max : contract;
}

/** The pointer of a list as a whole, which the contract refuses when it is too long. */
function listPointer(scope: Scope): string {
  return scope === "kept" ? "/kept_columns" : `/columns/${String(scope)}/labels`;
}

/**
 * The refusals of a list itself — the kept columns, or the labels of one of the columns read — by
 * list, the pointer designating no label. The draft is the one sent.
 */
function listRefusals(outcome: Outcome<unknown>, sent: Draft): ReadonlyMap<Scope, FieldProblem> {
  const refused = new Map<Scope, FieldProblem>();
  if (!("problem" in outcome)) {
    return refused;
  }
  const lists: readonly Scope[] = [...sent.columns.keys(), "kept"];
  for (const field of outcome.problem.fields ?? []) {
    const scope = lists.find((each) => listPointer(each) === field.pointer);
    if (scope !== undefined && field.code === "VALUE_TOO_LONG" && !refused.has(scope)) {
      refused.set(scope, field);
    }
  }
  return refused;
}

/** The pointer of every label of a draft, with the key of its row. */
function pointers(draft: Draft): readonly (readonly [string, number])[] {
  return [
    ...draft.columns.flatMap(({ rows }, scope) =>
      rows.map(({ key }, rank) => [pointer(scope, rank), key] as const),
    ),
    ...draft.kept.map(({ key }, rank) => [pointer("kept", rank), key] as const),
  ];
}

/**
 * The refusals of the server by field the form says at a label, by the key of its row — a pointer
 * names a rank of the form sent, which a removal moves —, and the outcome to tell under the form:
 * the refusal without the fields said already, none when every one is. The draft is the one sent.
 */
function placed(
  outcome: Outcome<unknown>,
  sent: Draft,
): { readonly refused: Map<number, FieldProblem>; readonly told: Outcome<unknown> | undefined } {
  const refused = new Map<number, FieldProblem>();
  if (!("problem" in outcome) || outcome.problem.fields === undefined) {
    return { refused, told: outcome };
  }
  const keys = new Map(pointers(sent));
  const rest = outcome.problem.fields.filter((problem) => {
    const key = keys.get(problem.pointer);
    // A second refusal of the same label stays in the rest, told under the form: none is lost.
    if (key === undefined || refused.has(key)) {
      return true;
    }
    refused.set(key, problem);
    return false;
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

/** The identifier of the command that saves, where the focus goes when no field holds it. */
const SAVE = "save";

/** The control of the form that holds the focus now, by the identifier it is registered under. */
function activeControl(controls: ReadonlyMap<string, HTMLElement>): string {
  return [...controls].find(([, element]) => element === document.activeElement)?.[0] ?? SAVE;
}

/** The form: a list of labels for each column read and one for the kept columns, sent whole. */
function MappingForm({
  mapping,
  onDone,
}: {
  readonly mapping: Mapping;
  readonly onDone: (answer: Mapping) => void;
}) {
  const t = useTranslations("reference.actualCostMapping");
  const column = useTranslations("enums.ActualCostSourceColumn");
  const held = useHeldCommand();
  const noteRefusal = useNoteRefusal();
  const [draft, setDraft] = useState(() => draftOf(mapping));
  // What the draft rests on: the version it is written from, and the draft as of the last send (or
  // as opened), by which a reading newer than that version is told to find it unchanged.
  const [basis, setBasis] = useState({ version: mapping.lock_version, draft });
  const [problems, setProblems] = useState<ReadonlyMap<number, FieldProblem>>(() => new Map());
  const [sent, setSent] = useState<components["schemas"]["ActualCostMappingWrite"]>();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [listProblems, setListProblems] = useState<ReadonlyMap<Scope, FieldProblem>>(
    () => new Map(),
  );
  // A command in the page, no transition (#1484): busy from the press to the answer, in one update.
  const [busy, setBusy] = useState(false);
  // A write lost once sent: the form waits until the screen has been read anew (US-2240).
  const reading = useReadAnew(outcome);
  const waiting = busy || reading;
  // A reading newer than the version the draft rests on takes the place of the draft while the
  // draft has not changed since it was sent — a version stale, read anew —, without mounting the
  // form again by a `key`, which would lose the focus and what is typed meanwhile (#2266): adjusted
  // in the render, once, as React admits for a state drawn from a prop that changes.
  if (!busy && mapping.lock_version > basis.version && draft === basis.draft) {
    const read = draftOf(mapping);
    setDraft(read);
    setBasis({ version: mapping.lock_version, draft: read });
    setProblems(new Map());
    setSent(undefined);
    setOutcome(undefined);
    setListProblems(new Map());
  }
  const controls = useRef(new Map<string, HTMLElement>());
  // What takes the focus after a change: the field of a label, a command, a new one each time.
  const [focused, setFocused] = useState<{ readonly id: string }>();
  useEffect(() => {
    if (focused !== undefined) {
      (controls.current.get(focused.id) ?? controls.current.get(SAVE))?.focus();
    }
  }, [focused]);
  const register = (id: string, element: HTMLElement | null) => {
    if (element === null) {
      controls.current.delete(id);
    } else {
      controls.current.set(id, element);
    }
  };
  // The key of the next label, which a click on « add » focuses once it is rendered.
  const lastKey = draft.next - 1;
  const forget = (key: number) => {
    setProblems((before) => {
      if (!before.has(key)) {
        return before;
      }
      const rest = new Map(before);
      rest.delete(key);
      return rest;
    });
  };
  const update = (change: (before: Draft) => Draft, focus: string, removed?: number) => {
    setDraft(change);
    setListProblems(new Map());
    if (removed !== undefined) {
      forget(removed);
    }
    setFocused({ id: focus === "row-new" ? `row-${String(lastKey + 1)}` : focus });
  };
  const retype = (scope: Scope, key: number, text: string) => {
    forget(key);
    setListProblems((before) => {
      if (!before.has(scope)) {
        return before;
      }
      const rest = new Map(before);
      rest.delete(scope);
      return rest;
    });
    setDraft((before) =>
      changed(before, scope, (rows) =>
        rows.map((row) => (row.key === key ? { ...row, text } : row)),
      ),
    );
  };

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (waiting) {
      return;
    }
    // The control that holds the focus, which the fields held lose: it takes it back with the
    // answer.
    const active = activeControl(controls.current);
    setBusy(true);
    setOutcome(undefined);
    setListProblems(new Map());
    const sentDraft = draft;
    // From the version the draft rests on: a newer reading that did not replace a draft changed
    // since is not lent its version.
    const body = written(sentDraft, basis.version);
    setBasis((before) => ({ ...before, draft: sentDraft }));
    void held(setActualCostMapping(body), () => true).then((answer) => {
      // The answer and the fields active again, in one update.
      setBusy(false);
      if (answer.kind === "done") {
        setProblems(new Map());
        setSent(undefined);
        setFocused({ id: active });
        // The draft stays, as it was sent, on the version the answer brings: the page read anew at
        // that version changes nothing of it.
        setBasis({ version: answer.data.lock_version, draft: sentDraft });
        onDone(answer.data);
        return;
      }
      const told = placed(answer, sentDraft);
      if (told.refused.size > 0) {
        noteRefusal(answer, { parts: [told.told] });
        const first = pointers(sentDraft).find(([, key]) => told.refused.has(key));
        if (first !== undefined) {
          setFocused({ id: `row-${String(first[1])}` });
        }
      } else {
        setFocused({ id: active });
      }
      setSent(body);
      setListProblems(listRefusals(answer, sentDraft));
      setProblems(told.refused);
      setOutcome(told.told);
    });
  };

  const common = { problems, sent, register, update, retype };
  return (
    <form
      aria-label={t("form")}
      noValidate
      aria-busy={waiting}
      onSubmit={submit}
      className="flex min-w-0 flex-col gap-7"
    >
      <SectionCard title={t("readColumns")} icon={Columns3}>
        <div className="grid gap-5">
          {draft.columns.map(({ column: each, required, rows }, scope) => (
            <fieldset key={each} disabled={waiting} className="grid min-w-0 gap-2">
              <legend className="mb-1 text-sm font-semibold">
                {column(each)}{" "}
                <span className="font-normal text-muted-foreground">
                  {required ? t("required") : t("optional")}
                </span>
              </legend>
              <LabelList
                {...common}
                scope={scope}
                rows={rows}
                name={column(each)}
                listProblem={listProblems.get(scope)}
              />
            </fieldset>
          ))}
        </div>
      </SectionCard>
      <SectionCard title={t("kept")} icon={TableProperties}>
        <fieldset disabled={waiting} className="grid min-w-0 gap-2">
          <legend className="sr-only">{t("kept")}</legend>
          <p className="text-sm text-muted-foreground">{t("keptHint")}</p>
          <LabelList
            {...common}
            scope="kept"
            rows={draft.kept}
            name={t("kept")}
            listProblem={listProblems.get("kept")}
          />
        </fieldset>
      </SectionCard>
      <OutcomeNotice
        outcome={outcome}
        reading={reading}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
      <div>
        <Button
          type="submit"
          disabled={waiting}
          aria-busy={waiting}
          ref={(element) => {
            register(SAVE, element);
          }}
        >
          <Save aria-hidden="true" />
          {waiting ? t("saving") : t("save")}
        </Button>
      </div>
    </form>
  );
}

/**
 * Render the correspondence of the extraction of the actual costs: the bar of the columns required
 * without a label, then the lists — a form for a session that may modify the cost settings.
 */
export function ActualCostMapping({
  mapping,
  writes,
}: {
  readonly mapping: Mapping;
  /** Whether the session holds `cost_settings.write`. */
  readonly writes: boolean;
}) {
  const t = useTranslations("reference.actualCostMapping");
  const [answered, setAnswered] = useState<Mapping>();
  const [said, say] = useSaid();
  const shown =
    answered !== undefined && answered.lock_version > mapping.lock_version ? answered : mapping;
  return (
    <>
      <p className="text-sm text-muted-foreground">{t("summary")}</p>
      <RequiredBar mapping={shown} />
      <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
        {said === undefined ? null : <span key={said.count}>{said.text}</span>}
      </p>
      {writes ? (
        <MappingForm
          // Not mounted again by a `key` on the version: a reading newer than the one the draft
          // rests on is taken by the form itself, when the draft has not changed since it was sent.
          mapping={shown}
          onDone={(answer) => {
            setAnswered((before) =>
              before === undefined || before.lock_version < answer.lock_version ? answer : before,
            );
            // No object named: the mapping of the costs is one of the project, not an object of a
            // list.
            say(t("saved"));
          }}
        />
      ) : (
        <ReadMapping mapping={shown} />
      )}
    </>
  );
}
