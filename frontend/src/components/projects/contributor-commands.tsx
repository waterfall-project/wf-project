// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The modification of the contributors of a project (FBS-4.2.4, EP-02/L44b): the whole list, each
 * contributor with its capacity — project manager or contributor —, written at once
 * (`setContributors`, WF-PRJ-0060). It follows the command `manage_contributors` the project lists:
 * absent, nothing is offered; unavailable, the command is presented `aria-disabled`, described by
 * the conditions it lacks; available, it opens the list in a dialog, where a contributor changes
 * capacity or is withdrawn, and where the accounts the server proposes — those of the services whose
 * roles the lines of the estimate employ (WF-PRJ-0070), each with the node of organisation and the
 * roles it is proposed for (`org_node_label`, `resource_role_labels`, EP-14/L42i) — are inscribed one
 * by one, each confirmed by the project manager, as active as the server says the account is
 * (`is_active`): nothing proposed is applied until the list is saved.
 *
 * The list is written from a reading of it whole, with its counter: a reading filtered has none,
 * and written back it would withdraw what it omits — the page then reads the list whole besides,
 * for the dialog to start from (`whole`). A list left without a project manager is refused before
 * anything is asked (WF-PRJ-0060); a refusal by field of the server (422, `/contributors/<n>/…`) is
 * said at the row of the account it points at, naming it — an account the installation does not
 * have (`UNKNOWN_USER`) or deactivated (`USER_INACTIVE`, WF-ADM-0060) —; any other refusal — no
 * project manager left (409), the version stale (412) with the offer to read the page anew — under
 * the form, or, the dialog gone, under the head of the list. The list answered takes the place of
 * the rows of a reading whole while its counter is newer — against the fake back, which keeps
 * nothing, for as long as the screen stays (`MockupNotice`) —, and the page is read anew. Under a
 * grid sorted, the list answered comes in the order of the server, not that of the sort —
 * transitory against the real back, which the page read anew replaces; permanent against the fake
 * back.
 *
 * The dialog starts from the reading it was opened on — its rows and its counter —, captured at the
 * opening, as `Opened.row` of the sub-projects: a reading newer that arrives while it is open changes
 * neither what it shows nor the counter it sends, which the server then refuses (412, WF-IHM-0110).
 * An answer closes only the dialog it was sent from, never one opened since (#660, #672).
 */
"use client";

import { Save, UserMinus, UserPlus, Users, X } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import {
  createContext,
  type MouseEvent,
  type ReactNode,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";

import { setContributors } from "@/api/actions/projects";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { UnmetConditions } from "@/components/commands/command";
import { type CommandOffer, UNAVAILABLE, unmetId } from "@/components/commands/offer";
import { OutcomeNotice } from "@/components/commands/outcome-notice";
import { rejected } from "@/components/commands/rejection";
import { ActiveState } from "@/components/reference/section";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { NativeSelect } from "@/components/ui/native-select";
import { formatLocale } from "@/i18n/format";
import { problemMessage } from "@/i18n/problem";

import { type Contributor, KINDS } from "./settings-grids";

type Schemas = components["schemas"];

/** The list of the contributors of a project and its counter, null for a reading filtered. */
export type ContributorReading = Schemas["ContributorList"];

/** A contributor proposed from the roles the estimate employs (WF-PRJ-0070). */
export type Suggestion = Schemas["ContributorSuggestion"];

/** A refusal of one field. */
type FieldProblem = Schemas["FieldProblem"];

/** The pointer of a refusal by field at a contributor of the list sent: its place in it. */
const AT_CONTRIBUTOR = /^\/contributors\/(\d+)(?:\/|$)/;

/** What the list of the contributors is written from, for the project it is of. */
export interface ContributorEditing {
  readonly project: string;
  /** The command `manage_contributors` the project lists: absent, nothing is offered. */
  readonly offer: CommandOffer | undefined;
  /** The counter of the reading the grid shows: null when it is filtered. */
  readonly counter: number | null;
  /** The list read whole, which a write starts from; none when the page has not read it. */
  readonly whole: ContributorReading | undefined;
  readonly suggestions: readonly Suggestion[];
}

/** The modification open: the reading whole it starts from, with its counter, and what opened it. */
interface Opened {
  readonly from: readonly Contributor[];
  readonly counter: number;
  readonly trigger: HTMLElement;
  /** The how-many-th opening it is: what an answer closes, never a later one. */
  readonly opening: number;
}

/** What the commands of the list hold: what it was read from, what the server answered. */
interface Commands {
  readonly editing: ContributorEditing;
  readonly answered: ContributorReading | undefined;
  readonly said: { readonly text: string; readonly count: number } | undefined;
  /** A refusal answered once the dialog is gone, told under the head of the list. */
  readonly refusal: Outcome<unknown> | undefined;
  readonly opened: Opened | undefined;
  readonly answer: (list: ContributorReading) => void;
  readonly say: (text: string) => void;
  readonly refuse: (refusal: Outcome<unknown> | undefined) => void;
  readonly open: (opened: Omit<Opened, "opening">) => void;
  /** Close the dialog; given an opening, only if it is still the one open. */
  readonly close: (opening?: number) => void;
}

/** The commands of the list of the contributors; none outside it. */
const ContributorContext = createContext<Commands | undefined>(undefined);

/** The accounts proposed that the rows do not count yet: an account inscribed is proposed no more. */
function proposedBesides(
  suggestions: readonly Suggestion[],
  rows: readonly Contributor[] | undefined,
) {
  return rows === undefined
    ? suggestions
    : suggestions.filter((one) => !rows.some((row) => row.user_id === one.user_id));
}

/** The newer of two lists, by their counters; the first when neither is newer. */
function newer(read: ContributorReading, answered: ContributorReading | undefined) {
  return answered?.lock_version != null &&
    read.lock_version !== null &&
    answered.lock_version > read.lock_version
    ? answered
    : read;
}

/**
 * The rows of the grid: those of the reading, or those the server answered a write with while its
 * counter is newer than that of a reading whole — a reading filtered shows what it retains.
 */
export function useContributorRows(rows: readonly Contributor[]): readonly Contributor[] {
  const commands = useContext(ContributorContext);
  const counter = commands?.editing.counter ?? null;
  if (commands?.answered === undefined || counter === null) {
    return rows;
  }
  const { answered } = commands;
  return answered.lock_version !== null && answered.lock_version > counter ? answered.items : rows;
}

/** The commands of the contributors of a project, for the list they hold; none without `editing`. */
export function ContributorCommands({
  editing,
  children,
}: {
  readonly editing: ContributorEditing | undefined;
  readonly children: ReactNode;
}) {
  const [answered, setAnswered] = useState<ContributorReading>();
  const [said, setSaid] = useState<Commands["said"]>();
  const [refusal, refuse] = useState<Outcome<unknown>>();
  const [opened, setOpened] = useState<Opened>();
  // How many times the dialog was opened: what tells an opening from the next.
  const openings = useRef(0);
  const commands = useMemo<Commands | undefined>(
    () =>
      editing && {
        editing,
        answered,
        said,
        refusal,
        opened,
        answer: (list) => {
          setAnswered((before) => (before === undefined ? list : newer(before, list)));
        },
        say: (text) => {
          setSaid((before) => ({ text, count: (before?.count ?? 0) + 1 }));
        },
        refuse,
        open: (next) => {
          openings.current += 1;
          setOpened({ ...next, opening: openings.current });
        },
        close: (opening) => {
          setOpened((current) =>
            opening === undefined || current?.opening === opening ? undefined : current,
          );
        },
      },
    [editing, answered, said, refusal, opened],
  );
  return <ContributorContext value={commands}>{children}</ContributorContext>;
}

/**
 * The command that modifies the list, as the project lists `manage_contributors`: unavailable, with
 * the conditions it lacks; available once the list is read whole, with its counter — the reading the
 * dialog starts from, captured when the command is pressed.
 */
function ModifyContributors({
  commands,
  from,
}: {
  readonly commands: Commands;
  readonly from: ContributorReading | undefined;
}) {
  const t = useTranslations("projectLists.contributors");
  const id = useId();
  const { offer } = commands.editing;
  // What the dialog starts from: the rows and the counter of the reading, whole.
  const reading =
    from?.lock_version == null ? undefined : { from: from.items, counter: from.lock_version };
  if (offer === undefined || (offer.is_available && reading === undefined)) {
    return null;
  }
  const unmet = unmetId(offer, id);
  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        aria-disabled={offer.is_available ? undefined : true}
        aria-describedby={unmet}
        className={UNAVAILABLE}
        onClick={(event: MouseEvent<HTMLElement>) => {
          if (offer.is_available && reading !== undefined) {
            commands.refuse(undefined);
            commands.open({ ...reading, trigger: event.currentTarget });
          }
        }}
      >
        <Users aria-hidden="true" />
        {t("modify")}
      </Button>
      <UnmetConditions id={unmet} offer={offer} />
    </>
  );
}

/**
 * The head of the list: the region that says what the last write did, the command that modifies the
 * list, the accounts the server proposes, a refusal answered once the dialog is gone, and the dialog.
 */
export function ContributorHead() {
  const t = useTranslations("projectLists.contributors");
  const locale = useLocale();
  const commands = useContext(ContributorContext);
  if (commands === undefined) {
    return null;
  }
  const { said, editing } = commands;
  const { suggestions } = editing;
  // A modification opens on the list read whole, whose counter it sends; the newer one answered after.
  const from = editing.whole === undefined ? undefined : newer(editing.whole, commands.answered);
  // Proposed under the list: the accounts the list it opens on does not count — inscribed, no more.
  const proposed = proposedBesides(suggestions, from?.items);
  return (
    <div className="space-y-2">
      <div className="flex flex-wrap items-center gap-2">
        <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
          {said === undefined ? null : <span key={said.count}>{said.text}</span>}
        </p>
        <ModifyContributors commands={commands} from={from} />
      </div>
      {proposed.length === 0 ? null : (
        <p className="text-sm text-muted-foreground">
          {t("suggested", {
            count: proposed.length,
            names: new Intl.ListFormat(formatLocale(locale), { type: "conjunction" }).format(
              proposed.map((suggestion) => suggestion.display_name),
            ),
          })}
        </p>
      )}
      <OutcomeNotice
        outcome={commands.refusal}
        onClear={() => {
          commands.refuse(undefined);
        }}
        dismissible
      />
      {commands.opened === undefined ? null : (
        <ContributorEditor
          key={commands.opened.opening}
          commands={commands}
          opened={commands.opened}
          suggestions={suggestions}
        />
      )}
    </div>
  );
}

/** The dialog that modifies the list of the contributors, from the reading it was opened on. */
function ContributorEditor({
  commands,
  opened,
  suggestions,
}: {
  readonly commands: Commands;
  readonly opened: Opened;
  readonly suggestions: readonly Suggestion[];
}) {
  const t = useTranslations("projectLists.contributors");
  const form = useTranslations("reference.form");
  const kinds = useTranslations("enums.ContributorKind");
  const locale = useLocale();
  const messages = useMessages();
  const [draft, setDraft] = useState<readonly Contributor[]>(opened.from);
  const [problems, setProblems] = useState<ReadonlyMap<string, FieldProblem>>(() => new Map());
  const [outcome, setOutcome] = useState<Outcome<unknown>>();
  const [pending, startTransition] = useTransition();
  const first = useRef<HTMLSelectElement>(null);
  const table = useRef<HTMLTableElement>(null);
  const open = useRef(true);
  const id = useId();
  // The first row a refusal by field points at takes the focus, as a field of a form does.
  useEffect(() => {
    table.current?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus();
  }, [problems]);
  const proposed = proposedBesides(suggestions, draft);
  const close = () => {
    open.current = false;
    commands.close();
  };

  const submit = () => {
    if (pending) {
      return;
    }
    setProblems(new Map());
    // A project keeps a project manager (WF-PRJ-0060): refused before anything is asked.
    if (!draft.some((row) => row.kind === "project_manager")) {
      setOutcome({
        kind: "refused",
        problem: { code: "LAST_PROJECT_MANAGER", status: 409 },
        conflictingObjectId: null,
      });
      first.current?.focus();
      return;
    }
    setOutcome(undefined);
    const sent = draft;
    startTransition(async () => {
      const answer = await setContributors(commands.editing.project, {
        contributors: sent.map(({ user_id, kind }) => ({ user_id, kind })),
        lock_version: opened.counter,
      }).catch(rejected);
      if (answer.kind === "done") {
        commands.answer(answer.data);
        commands.say(t("saved"));
        // Closed if it is still the opening the answer was sent from, never a later one.
        open.current = false;
        commands.close(opened.opening);
      } else if (!open.current) {
        commands.refuse(answer);
      } else {
        const placed = new Map<string, FieldProblem>();
        const rest = ("problem" in answer ? (answer.problem.fields ?? []) : []).filter((field) => {
          const at = AT_CONTRIBUTOR.exec(field.pointer)?.[1];
          const row = at === undefined ? undefined : sent[Number(at)];
          if (row !== undefined) {
            placed.set(row.user_id, field);
          }
          return row === undefined;
        });
        setProblems(placed);
        // What is said at a row is not said again under the form; the rest of the refusal is.
        if (placed.size === 0 || !("problem" in answer)) {
          setOutcome(answer);
        } else if (rest.length > 0) {
          setOutcome({ ...answer, problem: { ...answer.problem, fields: rest } });
        }
      }
    });
  };

  return (
    <Dialog
      open
      onOpenChange={(opened) => {
        if (!opened) {
          close();
        }
      }}
    >
      <DialogContent
        aria-busy={pending}
        onCloseAutoFocus={(event) => {
          event.preventDefault();
          if (opened.trigger.isConnected) {
            opened.trigger.focus();
          }
        }}
      >
        <DialogHeader>
          <DialogTitle>{t("modify")}</DialogTitle>
          <DialogDescription>{t("formHint")}</DialogDescription>
        </DialogHeader>
        <table ref={table} aria-label={t("draft")} className="w-full text-sm">
          <tbody>
            {draft.map((row, index) => {
              const problem = problems.get(row.user_id);
              const said = `${id}-${row.user_id}`;
              return (
                <tr key={row.user_id} className="align-top">
                  <th scope="row" className="py-1 pr-2 text-left font-normal">
                    {row.display_name} {row.is_active ? null : <ActiveState active={false} />}
                    {problem === undefined ? null : (
                      <p id={said} className="text-destructive">
                        {t("refusedFor", {
                          name: row.display_name,
                          problem: problemMessage(problem, { locale, messages }),
                        })}
                      </p>
                    )}
                  </th>
                  <td className="py-1 pr-2">
                    <NativeSelect
                      ref={index === 0 ? first : undefined}
                      aria-label={t("kindOf", { name: row.display_name })}
                      aria-invalid={problem === undefined ? undefined : true}
                      aria-describedby={problem === undefined ? undefined : said}
                      value={row.kind}
                      onChange={(event) => {
                        const kind = KINDS.find((each) => each === event.target.value) ?? row.kind;
                        setDraft(draft.map((each) => (each === row ? { ...each, kind } : each)));
                      }}
                    >
                      {KINDS.map((kind) => (
                        <option key={kind} value={kind}>
                          {kinds(kind)}
                        </option>
                      ))}
                    </NativeSelect>
                  </td>
                  <td className="py-1">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      aria-label={t("withdraw", { name: row.display_name })}
                      onClick={() => {
                        setDraft(draft.filter((each) => each !== row));
                      }}
                    >
                      <UserMinus aria-hidden="true" />
                    </Button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {proposed.length === 0 ? null : (
          <section aria-label={t("proposals")} className="space-y-1">
            <h3 className="text-sm font-medium">{t("proposals")}</h3>
            <ul className="space-y-1">
              {proposed.map((one) => (
                <li key={one.user_id} className="flex items-center justify-between gap-2 text-sm">
                  <span>
                    {one.display_name}
                    <span className="block text-xs text-muted-foreground">
                      {t("proposedFrom", {
                        node: one.org_node_label,
                        count: one.resource_role_labels.length,
                        roles: new Intl.ListFormat(formatLocale(locale), {
                          type: "conjunction",
                        }).format(one.resource_role_labels),
                      })}
                    </span>
                  </span>
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      // Inscribed as the server tells the account (EP-14/L42i): active, a
                      // deactivated one being no longer proposed (WF-ADM-0060).
                      setDraft([
                        ...draft,
                        {
                          user_id: one.user_id,
                          display_name: one.display_name,
                          kind: "contributor",
                          is_active: one.is_active,
                        },
                      ]);
                    }}
                  >
                    <UserPlus aria-hidden="true" />
                    {t("inscribe", { name: one.display_name })}
                  </Button>
                </li>
              ))}
            </ul>
          </section>
        )}
        <OutcomeNotice
          outcome={outcome}
          onClear={() => {
            setOutcome(undefined);
          }}
          onDismissed={close}
        />
        <DialogFooter>
          <Button type="button" variant="outline" onClick={close}>
            <X aria-hidden="true" />
            {form("cancel")}
          </Button>
          <Button type="button" aria-busy={pending} onClick={submit}>
            <Save aria-hidden="true" />
            {form(pending ? "sending" : "save")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
