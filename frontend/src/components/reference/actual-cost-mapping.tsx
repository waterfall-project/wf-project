// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The correspondence of the extraction of the actual costs (FBS-3.1.3, WF-REF-0190, US-0620): for
 * each of the five columns Waterfall reads, the labels under which the ERP names it, and the labels
 * of the columns it keeps for information, declared one by one. A bar says the columns required that
 * have no label, as the server computes them (`is_complete`, `missing_columns`): the front computes
 * nothing of it, and takes it from the answer of a write as it takes it from the reading.
 *
 * A session that holds `cost_settings.write` adds, modifies and removes a label, and declares and
 * removes a kept column, in one form that replaces the correspondence whole with the version read
 * (`setActualCostMapping`); another reads the lists, with no command. The server alone judges the
 * labels: a refusal by field (422) is said at the label its pointer designates
 * (`/columns/<rank>/labels/<rank>`, `/kept_columns/<rank>`), the first one refused taking the focus,
 * a duplicate (`DUPLICATE_COLUMN_LABEL`) naming the label it doubles (`params.duplicate_of`); any other
 * refusal is told under the form — the version stale (412) with the offer to read the page anew,
 * which mounts the form again on what is read. The answer takes the place of the reading while it is
 * newer (`lock_version`).
 */
"use client";

import { Plus, Save, Trash2 } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import { type SubmitEvent, useEffect, useId, useRef, useState, useTransition } from "react";

import { setActualCostMapping } from "@/api/actions/reference";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { useHeldCommand } from "@/components/commands/held";
import { CommandTooltip } from "@/components/commands/command-tooltip";
import { OutcomeNotice, useNoteRefusal } from "@/components/commands/outcome-notice";
import { useSaid } from "@/components/notices/said";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { problemMessage } from "@/i18n/problem";

type Mapping = components["schemas"]["ActualCostMapping"];
type Source = components["schemas"]["ActualCostSourceColumn"];
type FieldProblem = components["schemas"]["FieldProblem"];

/** The longest label the contract takes. */
const LABEL_LENGTH = 200;

/** A label being typed, with a key of its own that keeps it through the removal of the ones before. */
interface Row {
  readonly key: number;
  readonly text: string;
}

/** A list of labels: the rank of a column read, or the kept columns. */
type Scope = number | "kept";

/** What the form holds: the labels of each column read, in the order of the contract, and the kept ones. */
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

/** The list of labels of a pointer of a write: the label it designates, and the column it belongs to. */
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
      <section aria-label={t("kept")} className="grid gap-1">
        <h3 className="text-sm font-semibold">{t("kept")}</h3>
        <ReadList labels={mapping.kept_columns} none={t("noKept")} />
      </section>
    </div>
  );
}

/** What the rows of a list need of the form that holds them. */
interface ListProps {
  readonly scope: Scope;
  readonly rows: readonly Row[];
  /** The name of the list the label of a row and its commands carry. */
  readonly name: string;
  readonly problems: ReadonlyMap<string, FieldProblem>;
  readonly sent: components["schemas"]["ActualCostMappingWrite"] | undefined;
  readonly register: (id: string, element: HTMLElement | null) => void;
  readonly update: (change: (draft: Draft) => Draft, focus: string) => void;
  readonly retype: (scope: Scope, key: number, text: string) => void;
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
function LabelList({ scope, rows, name, problems, sent, register, update, retype }: ListProps) {
  const t = useTranslations("reference.actualCostMapping");
  const commands = useTranslations("commands");
  const id = useId();
  const kept = scope === "kept";
  return (
    <div className="grid gap-2">
      <ul className="grid gap-2">
        {rows.map(({ key, text }, rank) => {
          const at = pointer(scope, rank);
          const problem = problems.get(at);
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
      <div>
        <CommandTooltip
          label={kept ? t("addKept") : t("add", { column: name })}
          help={commands("addMappingLabel.help")}
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

/**
 * The refusals of the server by field the form says at a label, by pointer, and the outcome to tell
 * under the form: the refusal without the fields said already, none when every one is.
 */
function placed(
  outcome: Outcome<unknown>,
  draft: Draft,
): { readonly refused: Map<string, FieldProblem>; readonly told: Outcome<unknown> | undefined } {
  const refused = new Map<string, FieldProblem>();
  if (!("problem" in outcome) || outcome.problem.fields === undefined) {
    return { refused, told: outcome };
  }
  const shown = new Set([
    ...draft.columns.flatMap(({ rows }, scope) => rows.map((_, rank) => pointer(scope, rank))),
    ...draft.kept.map((_, rank) => pointer("kept", rank)),
  ]);
  const rest = outcome.problem.fields.filter((problem) => {
    if (shown.has(problem.pointer)) {
      refused.set(problem.pointer, problem);
    }
    return !shown.has(problem.pointer);
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
  const [problems, setProblems] = useState<ReadonlyMap<string, FieldProblem>>(() => new Map());
  const [sent, setSent] = useState<components["schemas"]["ActualCostMappingWrite"]>();
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const controls = useRef(new Map<string, HTMLElement>());
  // What takes the focus after a change: the field of a label, a command, a new one each time.
  const [focused, setFocused] = useState<{ readonly id: string }>();
  useEffect(() => {
    if (focused !== undefined) {
      controls.current.get(focused.id)?.focus();
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
  const update = (change: (before: Draft) => Draft, focus: string) => {
    setDraft(change);
    setFocused({ id: focus === "row-new" ? `row-${String(lastKey + 1)}` : focus });
  };
  const retype = (scope: Scope, key: number, text: string) => {
    setDraft((before) =>
      changed(before, scope, (rows) =>
        rows.map((row) => (row.key === key ? { ...row, text } : row)),
      ),
    );
  };

  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    setOutcome(undefined);
    const body = written(draft, mapping.lock_version);
    startTransition(async () => {
      const answer = await held(setActualCostMapping(body), () => true);
      startTransition(() => {
        if (answer.kind === "done") {
          setProblems(new Map());
          setSent(undefined);
          onDone(answer.data);
          return;
        }
        const told = placed(answer, draft);
        if (told.refused.size > 0) {
          noteRefusal(answer, { parts: [told.told] });
          const first = [
            ...draft.columns.flatMap(({ rows }, scope) =>
              rows.map(({ key }, rank) => [key, pointer(scope, rank)] as const),
            ),
            ...draft.kept.map(({ key }, rank) => [key, pointer("kept", rank)] as const),
          ].find(([, at]) => told.refused.has(at));
          if (first !== undefined) {
            setFocused({ id: `row-${String(first[0])}` });
          }
        }
        setSent(body);
        setProblems(told.refused);
        setOutcome(told.told);
      });
    });
  };

  const common = { problems, sent, register, update, retype };
  return (
    <form
      aria-label={t("form")}
      noValidate
      aria-busy={pending}
      onSubmit={submit}
      className="grid gap-5"
    >
      {draft.columns.map(({ column: each, required, rows }, scope) => (
        <fieldset key={each} className="grid gap-2">
          <legend className="mb-1 text-sm font-semibold">
            {column(each)}{" "}
            <span className="font-normal text-muted-foreground">
              {required ? t("required") : t("optional")}
            </span>
          </legend>
          <LabelList {...common} scope={scope} rows={rows} name={column(each)} />
        </fieldset>
      ))}
      <fieldset className="grid gap-2">
        <legend className="mb-1 text-sm font-semibold">{t("kept")}</legend>
        <p className="text-xs text-muted-foreground">{t("keptHint")}</p>
        <LabelList {...common} scope="kept" rows={draft.kept} name={t("kept")} />
      </fieldset>
      <OutcomeNotice
        outcome={outcome}
        onClear={() => {
          setOutcome(undefined);
        }}
      />
      <div>
        <Button type="submit" aria-busy={pending}>
          <Save aria-hidden="true" />
          {pending ? t("saving") : t("save")}
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
          // A reading newer than the one the form opened on mounts it again on what is read.
          key={mapping.lock_version}
          mapping={shown}
          onDone={(answer) => {
            setAnswered((before) =>
              before === undefined || before.lock_version < answer.lock_version ? answer : before,
            );
            say(t("saved"));
          }}
        />
      ) : (
        <ReadMapping mapping={shown} />
      )}
    </>
  );
}
