// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The work breakdown edited in its grid (FBS-4.2.1, EP-14/L44c): a work package added, an order item
 * added to a work package, a deliverable to an order item, an element renamed or deleted, from the
 * menu of a cell — on its row — and from the bar of the grid — on the row of the active cell. Each
 * gesture sends the work breakdown whole (`setWorkBreakdown`), made on its reading whole and with its
 * counter — a reading filtered has none, and the page then reads it whole besides (`whole`, decision
 * of EP-02/L42f) —, an element added sent without an identifier, which the server gives it
 * (WF-DAT-0060). They follow the command `update_work_breakdown` the project lists: absent, nothing
 * is offered; unavailable — a terminal project, a background task that writes in the revision in
 * progress or freezes it (EP-14/L42s) —, presented `aria-disabled`, described by the conditions it
 * lacks.
 *
 * The deletion of an element is confirmed first; that of a work package or of an order item says that
 * the tasks of the revision in progress that bear it remain and lose their attachment, the marked
 * revisions keeping it (WF-PLA-0170) — the reading does not say whether a task bears it, so every one
 * says so. The work breakdown answered, read whole, takes the place of the rows of a reading whole
 * while its counter is newer — against the fake back, which keeps nothing, for as long as the screen
 * stays (`MockupNotice`) —, and the page is read anew; a reading filtered shows what it retains.
 * A refusal by field that points at the element a dialog writes — its label, its identifier — is said
 * at its field; one that points at another element is said naming it, by its kind and its label
 * (`UNKNOWN_WORK_BREAKDOWN_ITEM`, `DUPLICATE_WORK_BREAKDOWN_ITEM`); any other — the version stale
 * (412) with the offer to read the page anew — as any outcome: under the dialog while it is open,
 * above the grid once it is gone, as is every refusal of a deletion.
 *
 * Every gesture writes from the counter of the reading its dialog opened on: while a write is under
 * way, the commands wait, inactive and saying why, for the dialog to open on the counter its answer
 * brings (#661, #734); an answer closes only the dialog it was sent from (#660, #672).
 */
"use client";

import { ListPlus, PencilLine, Plus, Save, Trash2, X } from "lucide-react";
import { useLocale, useMessages, useTranslations } from "next-intl";
import {
  createContext,
  type MouseEvent,
  type ReactNode,
  type SubmitEvent,
  useContext,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
  useTransition,
} from "react";

import { setWorkBreakdown } from "@/api/actions/projects";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { UnmetConditions, useUnmet } from "@/components/commands/command";
import { type CommandOffer, UNAVAILABLE, unmetId } from "@/components/commands/offer";
import { OutcomeNotice, useNoteRefusal } from "@/components/commands/outcome-notice";
import { rejected } from "@/components/commands/rejection";
import type { RowCommands } from "@/components/grid/undo-commands";
import { type Said, type Say, useSaid } from "@/components/notices/said";
import { WritingNote } from "@/components/reference/reference-form";
import { Button } from "@/components/ui/button";
import { ContextMenuItem, ContextMenuLabel } from "@/components/ui/context-menu";
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
import { problemMessage } from "@/i18n/problem";

import { type BreakdownWrite, edited, elementAt, type Gesture } from "./breakdown-edits";
import {
  type BreakdownKind,
  type BreakdownRow,
  breakdownRows,
  type WorkBreakdown,
} from "./settings-grids";

/** A refusal of one field. */
type FieldProblem = components["schemas"]["FieldProblem"];

/** The longest label of an element the contract takes. */
const LABEL_LENGTH = 300;

/** The kind of an element added under a parent; a work package under none. */
const CHILD: Readonly<Record<BreakdownKind | "root", BreakdownKind>> = {
  root: "work_package",
  work_package: "order_item",
  order_item: "deliverable",
  deliverable: "deliverable",
};

/** The cell a tree grid keeps active, the one stop of its tabulation. */
const ACTIVE_CELL = '[role="treegrid"] [tabindex="0"]';

/** What the work breakdown is written from, for the project it is of. */
export interface BreakdownEditing {
  readonly project: string;
  /** The command `update_work_breakdown` the project lists: absent, nothing is offered. */
  readonly offer: CommandOffer | undefined;
  /** The counter of the reading the grid shows: null when it is filtered. */
  readonly counter: number | null;
  /** The work breakdown read whole, which a gesture starts from; none when the page has not read it. */
  readonly whole: WorkBreakdown | undefined;
}

/** A dialog open: the gesture, the reading whole it is made on and its counter, what opened it. */
interface Opened {
  readonly gesture: Gesture;
  readonly from: WorkBreakdown;
  readonly counter: number;
  readonly trigger: HTMLElement | undefined;
  /** The section of the list, where the focus goes back when the trigger is gone. */
  readonly section: Element | null | undefined;
  /** The how-many-th opening it is: what an answer closes, never a later one. */
  readonly opening: number;
}

/** A refusal by field said naming the element it points at, by its kind and its label. */
interface Named {
  readonly kind: BreakdownKind;
  readonly label: string;
  readonly problem: FieldProblem;
}

/** A refusal of a write: what points at another element, said naming it, and the rest. */
interface Refusal {
  readonly outcome: Outcome<unknown>;
  readonly named: readonly Named[];
}

/** What the commands of the work breakdown hold: what it was read from, what the server answered. */
interface Commands {
  readonly editing: BreakdownEditing;
  readonly answered: WorkBreakdown | undefined;
  readonly said: Said | undefined;
  /** A refusal answered once the dialog is gone, or of a deletion, told above the grid. */
  readonly refusal: Refusal | undefined;
  readonly opened: Opened | undefined;
  /** Whether a write is under way: the commands wait for its answer. */
  readonly writing: boolean;
  readonly answer: (reading: WorkBreakdown) => void;
  readonly write: (writing: boolean) => void;
  readonly say: Say;
  readonly refuse: (refusal: Refusal | undefined) => void;
  readonly open: (gesture: Gesture, trigger: HTMLElement | undefined) => void;
  /** Close the dialog; given an opening, only if it is still the one open. */
  readonly close: (opening?: number) => void;
}

/** The commands of the work breakdown of a project; none outside it. */
const BreakdownContext = createContext<Commands | undefined>(undefined);

/** The newer of two readings, by their counters; the first when neither is newer. */
function newer(read: WorkBreakdown, answered: WorkBreakdown | undefined) {
  return answered?.lock_version != null &&
    read.lock_version !== null &&
    answered.lock_version > read.lock_version
    ? answered
    : read;
}

/** Give the focus to the active cell of the grid of a section, or to the section. */
function refocus(section: Element | null | undefined) {
  section?.querySelector<HTMLElement>(ACTIVE_CELL)?.focus();
}

/**
 * The rows of the grid: those of the reading, or those of the work breakdown the server answered a
 * write with, while its counter is newer than that of a reading whole — a reading filtered shows
 * what it retains.
 */
export function useBreakdownRows(rows: readonly BreakdownRow[]): readonly BreakdownRow[] {
  const commands = useContext(BreakdownContext);
  const counter = commands?.editing.counter ?? null;
  const answered = commands?.answered;
  return useMemo(
    () =>
      answered?.lock_version != null && counter !== null && answered.lock_version > counter
        ? breakdownRows(answered)
        : rows,
    [answered, counter, rows],
  );
}

/** The commands of the work breakdown of a project, for the grid they hold; none without `editing`. */
export function BreakdownCommands({
  editing,
  children,
}: {
  readonly editing: BreakdownEditing | undefined;
  readonly children: ReactNode;
}) {
  const [answered, setAnswered] = useState<WorkBreakdown>();
  const [said, say] = useSaid();
  const [refusal, refuse] = useState<Refusal>();
  const [opened, setOpened] = useState<Opened>();
  // How many times a dialog was opened: what tells an opening from the next.
  const openings = useRef(0);
  const [writing, write] = useState(false);
  const commands = useMemo<Commands | undefined>(
    () =>
      editing && {
        editing,
        answered,
        said,
        refusal,
        opened,
        writing,
        write,
        refuse,
        answer: (reading) => {
          setAnswered((before) => (before === undefined ? reading : newer(before, reading)));
        },
        say,
        open: (gesture, trigger) => {
          // A gesture is made on the reading whole, the newer one answered after it.
          const from = editing.whole === undefined ? undefined : newer(editing.whole, answered);
          if (from?.lock_version == null) {
            return;
          }
          openings.current += 1;
          refuse(undefined);
          const section = trigger?.closest("section");
          setOpened({
            gesture,
            from,
            counter: from.lock_version,
            trigger,
            section,
            opening: openings.current,
          });
        },
        close: (opening) => {
          setOpened((current) =>
            opening === undefined || current?.opening === opening ? undefined : current,
          );
        },
      },
    [editing, answered, said, say, refusal, opened, writing],
  );
  return <BreakdownContext value={commands}>{children}</BreakdownContext>;
}

/** A command on a row: its accessible name, its text, its icon, and the gesture it opens. */
interface RowCommand {
  readonly key: string;
  readonly name: string;
  readonly text: string;
  readonly icon: ReactNode;
  readonly gesture: Gesture;
}

/**
 * The commands on a row — none outside one —: a work package added; under a work package or an
 * order item, an element added to it; the row renamed, deleted.
 */
function useRowCommands(): (row: BreakdownRow | undefined) => readonly RowCommand[] {
  const t = useTranslations("projectLists.workBreakdown");
  return (row) => {
    const workPackage: RowCommand = {
      key: "workPackage",
      name: t("createWorkPackage"),
      text: t("createWorkPackage"),
      icon: <Plus aria-hidden="true" />,
      gesture: { kind: "add", parent: undefined },
    };
    if (row === undefined) {
      return [workPackage];
    }
    const element = t("element", { kind: row.kind, label: row.label });
    const add: RowCommand = {
      key: "add",
      name: t("addUnder", { kind: row.kind, label: row.label }),
      text: t("add", { kind: row.kind }),
      icon: <ListPlus aria-hidden="true" />,
      gesture: { kind: "add", parent: row },
    };
    return [
      workPackage,
      ...(row.kind === "deliverable" ? [] : [add]),
      {
        key: "rename",
        name: t("renameNamed", { element }),
        text: t("rename"),
        icon: <PencilLine aria-hidden="true" />,
        gesture: { kind: "rename", row },
      },
      {
        key: "delete",
        name: t("deleteNamed", { element }),
        text: t("delete"),
        icon: <Trash2 aria-hidden="true" />,
        gesture: { kind: "delete", row },
      },
    ];
  };
}

/**
 * The commands the grid of the work breakdown gives its rows, as the project lists
 * `update_work_breakdown`: none when it does not list it, or lists it available before the work
 * breakdown is read whole; unavailable, with the conditions it lacks; waiting, inactive and saying
 * why, while a write is under way, whose answer brings the counter (#661, #734).
 */
export function useBreakdownCommands(): RowCommands<BreakdownRow> | undefined {
  const form = useTranslations("reference.form");
  const unmet = useUnmet();
  const commands = useContext(BreakdownContext);
  const on = useRowCommands();
  const id = useId();
  const offer = commands?.editing.offer;
  if (commands === undefined || offer === undefined) {
    return undefined;
  }
  if (offer.is_available && commands.editing.whole === undefined) {
    return undefined;
  }
  const { writing } = commands;
  const waiting = writing || !offer.is_available;
  const why = writing ? `${id}-writing` : unmetId(offer, id);
  return {
    bar: (row) => (
      <div className="flex flex-wrap items-center gap-1">
        {on(row).map((command) => (
          <Button
            key={command.key}
            type="button"
            variant="outline"
            size="sm"
            aria-label={command.name}
            aria-disabled={waiting ? true : undefined}
            aria-busy={writing}
            aria-describedby={why}
            className={`h-7 text-xs ${UNAVAILABLE}`}
            onClick={(event: MouseEvent<HTMLElement>) => {
              if (!waiting) {
                commands.open(command.gesture, event.currentTarget);
              }
            }}
          >
            {command.icon}
            {command.text}
          </Button>
        ))}
        {writing ? null : <UnmetConditions id={why} offer={offer} />}
        <WritingNote id={`${id}-writing`} writing={writing} />
      </div>
    ),
    menu: (row, { cell, took }) => (
      <>
        {why === undefined ? null : (
          <ContextMenuLabel id={`${id}-menu`} className="text-xs font-normal text-muted-foreground">
            {writing ? form("writing") : unmet(offer)}
          </ContextMenuLabel>
        )}
        {on(row).map((command) => (
          <ContextMenuItem
            key={command.key}
            aria-disabled={waiting ? true : undefined}
            aria-describedby={why === undefined ? undefined : `${id}-menu`}
            className={UNAVAILABLE}
            onSelect={(event) => {
              // Pressed while it waits, it does nothing, and the menu stays open on why.
              if (waiting) {
                event.preventDefault();
                return;
              }
              took();
              commands.open(command.gesture, cell);
            }}
          >
            {command.icon}
            {command.name}
          </ContextMenuItem>
        ))}
      </>
    ),
  };
}

/**
 * The refusal of a write split by where it is said: what points at the element the dialog writes —
 * at its field while it is open —, what points at another element, named, and the rest; nothing left
 * to tell under the dialog when its field says all.
 */
function split(
  answer: Outcome<unknown>,
  sent: BreakdownWrite,
  at: string | undefined,
): { readonly field: FieldProblem | undefined; readonly refusal: Refusal | undefined } {
  if (!("problem" in answer) || answer.problem.fields === undefined) {
    return { field: undefined, refusal: { outcome: answer, named: [] } };
  }
  let field: FieldProblem | undefined;
  const named: Named[] = [];
  const rest: FieldProblem[] = [];
  for (const problem of answer.problem.fields) {
    const element = elementAt(sent, problem.pointer);
    if (element === undefined) {
      rest.push(problem);
    } else if (element.pointer === at && field === undefined) {
      field = problem;
    } else {
      named.push({ kind: element.kind, label: element.label, problem });
    }
  }
  const outcome = { ...answer, problem: { ...answer.problem, fields: rest } };
  return {
    field,
    refusal:
      field !== undefined && named.length === 0 && rest.length === 0
        ? undefined
        : { outcome, named },
  };
}

/** Tell of a refusal of a write: each element it points at named, then the rest as any outcome. */
function RefusalNotice({
  refusal,
  onClear,
  onDismissed,
  dismissible = false,
}: {
  readonly refusal: Refusal | undefined;
  readonly onClear: () => void;
  readonly onDismissed?: () => void;
  readonly dismissible?: boolean;
}) {
  const t = useTranslations("projectLists.workBreakdown");
  const locale = useLocale();
  const messages = useMessages();
  if (refusal === undefined) {
    return null;
  }
  return (
    <div className="space-y-1">
      <OutcomeNotice
        outcome={refusal.outcome}
        onClear={onClear}
        onDismissed={onDismissed}
        dismissible={dismissible}
      />
      {refusal.named.length === 0 ? null : (
        <div role="alert" className="space-y-1 text-sm text-destructive">
          {refusal.named.map(({ kind, label, problem }) => (
            <p key={problem.pointer}>
              {t("refusedFor", {
                kind,
                label,
                problem: problemMessage(problem, { locale, messages }),
              })}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

/**
 * Send the gesture of a dialog, from the reading it opened on, and take the answer: the work
 * breakdown answered, what was done said, and the dialog closed — if it is still the one open —; or
 * the refusal, said at the field of the dialog open, under it, or above the grid.
 */
function useSend(commands: Commands, opened: Opened) {
  const t = useTranslations("projectLists.workBreakdown");
  const [pending, startTransition] = useTransition();
  const [refusal, setRefusal] = useState<Refusal>();
  const noteRefusal = useNoteRefusal();
  const open = useRef(true);
  useEffect(() => {
    open.current = true;
    return () => {
      open.current = false;
    };
  }, []);
  const send = (label: string, onField: (problem: FieldProblem) => void) => {
    const { gesture } = opened;
    const { sent, at } = edited(opened.from, opened.counter, gesture, label);
    const told =
      gesture.kind === "add"
        ? { kind: CHILD[gesture.parent?.kind ?? "root"], label }
        : { kind: gesture.row.kind, label: gesture.kind === "rename" ? label : gesture.row.label };
    setRefusal(undefined);
    commands.write(true);
    startTransition(async () => {
      try {
        const answer = await setWorkBreakdown(commands.editing.project, sent).catch(rejected);
        if (answer.kind === "done") {
          commands.answer(answer.data);
          const done = { add: "added", rename: "renamed", delete: "deleted" } as const;
          commands.say(t(done[gesture.kind], told));
          commands.close(opened.opening);
        } else if (open.current && gesture.kind !== "delete") {
          const { field, refusal: rest } = split(answer, sent, at);
          if (field !== undefined) {
            // Said at its fields: noted whole, the notice of the rest noting nothing more.
            noteRefusal(answer, { subject: told.label, parts: [rest?.outcome] });
            onField(field);
          }
          setRefusal(rest);
        } else {
          // Gone, or a deletion confirmed: everything is told above the grid, naming its element.
          commands.refuse(split(answer, sent, undefined).refusal);
          commands.close(opened.opening);
        }
      } finally {
        commands.write(false);
      }
    });
  };
  return { pending, refusal, setRefusal, send };
}

/** The dialog that adds an element or renames one, by its label. */
function LabelDialog({
  commands,
  opened,
}: {
  readonly commands: Commands;
  readonly opened: Opened;
}) {
  const t = useTranslations("projectLists.workBreakdown");
  const form = useTranslations("reference.form");
  const locale = useLocale();
  const messages = useMessages();
  const id = useId();
  const { gesture } = opened;
  const [label, setLabel] = useState(gesture.kind === "add" ? "" : gesture.row.label);
  const [problem, setProblem] = useState<FieldProblem>();
  const input = useRef<HTMLInputElement>(null);
  const { pending, refusal, setRefusal, send } = useSend(commands, opened);
  const refuse = (refused: FieldProblem) => {
    setProblem(refused);
    input.current?.focus();
  };
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    const typed = label.trim();
    setProblem(undefined);
    if (typed === "") {
      setRefusal(undefined);
      refuse({ pointer: "/label", code: "VALUE_REQUIRED" });
      return;
    }
    send(typed, refuse);
  };
  const title =
    gesture.kind === "add"
      ? t("addTitle", { kind: gesture.parent?.kind ?? "root", label: gesture.parent?.label ?? "" })
      : t("renameNamed", {
          element: t("element", { kind: gesture.row.kind, label: gesture.row.label }),
        });
  return (
    <>
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
        <DialogDescription>{t("formHint")}</DialogDescription>
      </DialogHeader>
      <form aria-label={title} noValidate onSubmit={submit} className="grid gap-3">
        <div className="grid gap-1">
          <Label htmlFor={id}>{t("labelField")}</Label>
          <Input
            ref={input}
            id={id}
            value={label}
            maxLength={LABEL_LENGTH}
            aria-required
            aria-invalid={problem === undefined ? undefined : true}
            aria-describedby={problem === undefined ? undefined : `${id}-problem`}
            onChange={(event) => {
              setLabel(event.target.value);
            }}
          />
          {problem === undefined ? null : (
            <p id={`${id}-problem`} className="text-sm text-destructive">
              {problemMessage(problem, { locale, messages })}
            </p>
          )}
        </div>
        <RefusalNotice
          refusal={refusal}
          onClear={() => {
            setRefusal(undefined);
          }}
          onDismissed={() => {
            commands.close();
          }}
        />
        <DialogFooter>
          <Button
            type="button"
            variant="outline"
            onClick={() => {
              commands.close();
            }}
          >
            <X aria-hidden="true" />
            {form("cancel")}
          </Button>
          <Button type="submit" aria-busy={pending}>
            {gesture.kind === "add" ? <Plus aria-hidden="true" /> : <Save aria-hidden="true" />}
            {form(pending ? "sending" : gesture.kind === "add" ? "create" : "save")}
          </Button>
        </DialogFooter>
      </form>
    </>
  );
}

/** The confirmation of the deletion of an element, which says what goes with it. */
function DeleteConfirmation({
  commands,
  opened,
  row,
}: {
  readonly commands: Commands;
  readonly opened: Opened;
  readonly row: BreakdownRow;
}) {
  const t = useTranslations("projectLists.workBreakdown");
  const form = useTranslations("reference.form");
  const { pending, send } = useSend(commands, opened);
  return (
    <>
      <DialogHeader>
        <DialogTitle>
          {t("deleteTitle", { element: t("element", { kind: row.kind, label: row.label }) })}
        </DialogTitle>
        <DialogDescription>{t("deleteHint", { kind: row.kind })}</DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            commands.close();
          }}
        >
          {form("cancel")}
        </Button>
        <Button
          type="button"
          aria-busy={pending}
          onClick={() => {
            if (!pending) {
              send(row.label, () => undefined);
            }
          }}
        >
          <Trash2 aria-hidden="true" />
          {pending ? form("sending") : t("delete")}
        </Button>
      </DialogFooter>
    </>
  );
}

/**
 * The head of the grid: the region that says what the last write did, rendered from the start so
 * that a reader of the screen hears it; a refusal told above the grid; and the dialog open, if any.
 */
export function BreakdownHead() {
  const commands = useContext(BreakdownContext);
  const head = useRef<HTMLDivElement>(null);
  if (commands === undefined) {
    return null;
  }
  const { said, opened } = commands;
  return (
    <div ref={head} className="space-y-2">
      <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
        {said === undefined ? null : <span key={said.count}>{said.text}</span>}
      </p>
      <RefusalNotice
        refusal={commands.refusal}
        onClear={() => {
          commands.refuse(undefined);
        }}
        onDismissed={() => {
          refocus(head.current?.closest("section"));
        }}
        dismissible
      />
      {opened === undefined ? null : (
        <Dialog
          key={opened.opening}
          open
          onOpenChange={(open) => {
            if (!open) {
              commands.close();
            }
          }}
        >
          <DialogContent
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              if (opened.trigger?.isConnected === true) {
                opened.trigger.focus();
              } else {
                refocus(opened.section);
              }
            }}
          >
            {opened.gesture.kind === "delete" ? (
              <DeleteConfirmation commands={commands} opened={opened} row={opened.gesture.row} />
            ) : (
              <LabelDialog commands={commands} opened={opened} />
            )}
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
}
