// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the lists of the reference data (EP-02/L43): create an object, modify one,
 * deactivate or reactivate one — none deletes it, the reference data deactivating rather than
 * deleting (WF-REF-0010, WF-DAT-0080). The creation and the modification follow the permission of
 * modification of the function of the list (`platformOffer`): the page offers them to a session that
 * holds it, and to no other (WF-IHM-0090); the activation follows the command each object lists
 * (`available_commands`), absent, available, or unavailable with the conditions it lacks.
 *
 * Each list has its commands (`CommandedList`): the form they open, one at a time — rendered in the
 * list by the dialog of its kind (`useListForm`) —, and the answers of the server to the writes of
 * its rows. Every write answered reads the page anew (`readAnew` of the server actions); a
 * modification or an activation answered takes the place of its row meanwhile, as long as the answer
 * is newer than the row the page read (`lock_version`), a reading that has caught up prevailing.
 * Against the fake back, which keeps nothing, a row answered so outlives the readings anew, which
 * serve what it served before (`MockupNotice`). A creation adds no row: the page read anew lists the
 * object where the server retains it. What a write did is said in the region of the list, the dialog
 * open or closed; a refusal answered once the dialog is gone, and the refusal of a command of a row,
 * are said above the list as that of a reactivation (`useListReport`). A dialog closed gives the
 * focus back where it was opened from: the cell of the row, the grid being one stop, or the command
 * of the creation.
 *
 * Every prop a server component hands is data — the kind of the list, the label of a command —, never
 * a function (défaut n° 12 de `typescript.md`). In a dense grid, a command is out of the order of
 * tabulation, the grid being one stop: Enter on its cell presses it (`CELL_COMMAND`).
 */
"use client";

import { Ban, PencilLine, Plus, RotateCcw } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  createContext,
  type MouseEvent,
  type ReactNode,
  useContext,
  useMemo,
  useState,
  useTransition,
} from "react";

import { setActivation } from "@/api/actions/reference";
import type { components } from "@/api/generated/schema";
import type { Outcome } from "@/api/problem";
import { findOffer, type ListedCommand } from "@/components/commands/offer";
import type { ObjectNames } from "@/components/commands/outcome-notice";
import { rejected } from "@/components/commands/rejection";
import { CELL_COMMAND } from "@/components/grid/grid-keyboard";
import { Button } from "@/components/ui/button";

import { CellCommand } from "./cell-command";
import {
  type ActivationTarget,
  idOf,
  isObject,
  type ReferenceKind,
  type ReferenceObject,
} from "./kinds";
import { UnavailableActivation, useListReport } from "./reactivation";
import { ActiveState } from "./section";

/**
 * The commands an object of the reference data lists: the one that changes its state, and, for a
 * nature or a category of cost, the change of its type (`CostTypeCommand`, `CostCategoryCommand`),
 * which its form reads.
 */
export type ReferenceCommands = readonly ListedCommand<
  | components["schemas"]["ReferenceCommand"]
  | components["schemas"]["CostTypeCommand"]
  | components["schemas"]["CostCategoryCommand"]
>[];

/**
 * The server answered the write of another object than the one written: an unexpected error of the
 * service, told as such, which nothing takes the place of the row for — as a cell answered for
 * another row (`cell-writes.ts`); a backup marked too (`backup-commands.tsx`).
 */
export const ANOTHER_OBJECT: Outcome<never> = {
  kind: "refused",
  problem: { code: "INTERNAL_ERROR", status: 500 },
  conflictingObjectId: null,
};

/** An object a refusal may name: the node to reactivate first, as the row shown names it. */
export interface Conflict {
  readonly id: string;
  readonly name: string;
}

/** The form a list has open: a creation, or the modification of a row, and what opened it. */
interface Opened {
  readonly row: ReferenceObject | undefined;
  /** The command pressed, which the focus goes back to — or its cell — once the dialog has closed. */
  readonly trigger: HTMLElement;
}

/** What a write of a list did, said in its region, and the how-many-th it was. */
export interface Said {
  readonly text: string;
  readonly count: number;
}

/** The commands of a list, its form open, and the answers of the server to the writes of its rows. */
interface Commands {
  readonly kind: ReferenceKind;
  readonly opened: Opened | undefined;
  readonly said: Said | undefined;
  readonly answers: ReadonlyMap<string, ReferenceObject>;
  /** Take the answers of the server to writes of rows: the newest answer of a row prevails. */
  readonly answer: (rows: readonly ReferenceObject[]) => void;
  readonly say: (text: string) => void;
  readonly open: (opened: Opened) => void;
  /** Close the form of an opening, if it is still the one open. */
  readonly close: (opened: Opened) => void;
}

/** The commands of the list that holds them; none outside a list of the reference data. */
const ListCommands = createContext<Commands | undefined>(undefined);

/**
 * The rows of a page, each replaced by the answer of the server to a write of it while the answer is
 * newer than the row read — against the fake back, which keeps nothing, for as long as the screen
 * stays.
 */
export function useAnswered<Row extends ReferenceObject>(rows: readonly Row[]): readonly Row[] {
  const commands = useContext(ListCommands);
  const answers = commands?.answers;
  const kind = commands?.kind;
  return useMemo(() => {
    if (answers === undefined || kind === undefined || answers.size === 0) {
      return rows;
    }
    return rows.map((row) => {
      const answer = answers.get(idOf(kind, row));
      // A list holds its own kind of object alone: the answer to a row is of the row's kind.
      return answer !== undefined && answer.lock_version > row.lock_version ? (answer as Row) : row;
    });
  }, [rows, answers, kind]);
}

/**
 * Give the focus back to what opened a form: the cell of a command of a row, or the command — the list
 * when the page read anew no longer holds it.
 */
export function focusBack(
  { trigger }: { readonly trigger: HTMLElement },
  list: (() => void) | undefined,
) {
  if (!trigger.isConnected) {
    list?.();
    return;
  }
  const cell = trigger.hasAttribute(CELL_COMMAND) ? trigger.closest<HTMLElement>("td") : null;
  (cell ?? trigger).focus();
}

/**
 * The commands of a list of a kind of object: its form, the region that says what a write did, and
 * the answers of the server to the writes of its rows.
 */
export function CommandedList({
  kind,
  children,
}: {
  readonly kind: ReferenceKind;
  readonly children: ReactNode;
}) {
  const [answers, setAnswers] = useState<ReadonlyMap<string, ReferenceObject>>(() => new Map());
  const [opened, setOpened] = useState<Opened>();
  const [said, setSaid] = useState<Said>();
  const commands = useMemo<Commands>(
    () => ({
      kind,
      opened,
      said,
      answers,
      answer: (rows) => {
        setAnswers((before) => {
          const newer = rows.filter((row) => {
            const known = before.get(idOf(kind, row));
            return known === undefined || known.lock_version < row.lock_version;
          });
          if (newer.length === 0) {
            return before;
          }
          const after = new Map(before);
          for (const row of newer) {
            after.set(idOf(kind, row), row);
          }
          return after;
        });
      },
      say: (text) => {
        setSaid((before) => ({ text, count: (before?.count ?? 0) + 1 }));
      },
      open: setOpened,
      close: (closing) => {
        setOpened((current) => (current === closing ? undefined : current));
      },
    }),
    [kind, opened, said, answers],
  );
  return <ListCommands value={commands}>{children}</ListCommands>;
}

/** What the dialog of a list renders its form with, while the list has one open. */
export interface ListForm {
  readonly kind: ReferenceKind;
  /** The object modified, as its row shows it; none for a creation. */
  readonly row: ReferenceObject | undefined;
  /** The command and the object a refusal answered once the dialog is gone is told for. */
  readonly target: string | undefined;
  /**
   * The answer of the server as the form takes it: the modification of another object than the one
   * modified is a failure of the service.
   */
  readonly answering: (answer: Outcome<ReferenceObject>) => Outcome<ReferenceObject>;
  /** Take the answer of the server, the dialog open or closed. */
  readonly onDone: (answer: ReferenceObject) => void;
  readonly onClose: () => void;
  /** Give the focus back where the dialog was opened from, once it has closed. */
  readonly onClosed: () => void;
}

/**
 * The form the list has open, for the dialog of its kind to render within the list, where a refusal
 * answered once the dialog is gone is told (`useListReport`); none while no form is open.
 */
export function useListForm(): ListForm | undefined {
  const t = useTranslations("reference.form");
  const commands = useContext(ListCommands);
  const list = useListReport();
  const opened = commands?.opened;
  if (commands === undefined || opened === undefined) {
    return undefined;
  }
  const { kind } = commands;
  const { row } = opened;
  return {
    kind,
    row,
    target: row === undefined ? undefined : `modify ${kind} ${idOf(kind, row)}`,
    answering: (answer) =>
      row !== undefined && answer.kind === "done" && !isObject(kind, answer.data, idOf(kind, row))
        ? ANOTHER_OBJECT
        : answer,
    onDone: (answer) => {
      if (row !== undefined) {
        commands.answer([answer]);
      }
      commands.say(t(row === undefined ? "created" : "saved", { name: answer.label, kind }));
      commands.close(opened);
    },
    onClose: () => {
      commands.close(opened);
    },
    onClosed: () => {
      focusBack(opened, list?.refocus);
    },
  };
}

/**
 * Run a command of a row from the reading it is pressed on: its answer takes the place of the rows it
 * names and is said in the region of the list; its refusal is told above the list, in place of the
 * one the same command on the same object had there (`target`).
 */
export function useRowCommand(
  target: string,
  names: ObjectNames,
): readonly [
  boolean,
  (
    action: () => Promise<Outcome<readonly ReferenceObject[]>>,
    said: (rows: readonly ReferenceObject[]) => string,
  ) => void,
] {
  const list = useListReport();
  const commands = useContext(ListCommands);
  const [pending, startTransition] = useTransition();
  const run = (
    action: () => Promise<Outcome<readonly ReferenceObject[]>>,
    said: (rows: readonly ReferenceObject[]) => string,
  ) => {
    if (pending) {
      return;
    }
    // The reading the command is pressed on: its refusal is told on it alone.
    const reading = list?.reading ?? "";
    startTransition(async () => {
      const outcome = await action().catch(rejected);
      if (outcome.kind === "done") {
        commands?.answer(outcome.data);
        commands?.say(said(outcome.data));
      } else {
        list?.report({ outcome, reading, names, target });
      }
    });
  };
  return [pending, run];
}

/**
 * The region that says what the last write of a list did, rendered from the start so that a reader of
 * the screen hears what is put in it, and taking no room while it says nothing.
 */
export function WrittenRegion({ said }: { readonly said: Said | undefined }) {
  return (
    <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
      {said === undefined ? null : <span key={said.count}>{said.text}</span>}
    </p>
  );
}

/**
 * The command that opens the creation of an object, in the head of the list that holds it — offered
 * on an empty list too —, after the region that says what the last write of the list did.
 */
export function CreateCommand({ label }: { readonly label: string }) {
  const commands = useContext(ListCommands);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <WrittenRegion said={commands?.said} />
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={(event: MouseEvent<HTMLElement>) => {
          commands?.open({ row: undefined, trigger: event.currentTarget });
        }}
      >
        <Plus aria-hidden="true" />
        {label}
      </Button>
    </div>
  );
}

/** The command that opens the modification of a row, named after it. */
export function ModifyCommand({ row }: { readonly row: ReferenceObject }) {
  const t = useTranslations("reference");
  const commands = useContext(ListCommands);
  return (
    <CellCommand
      aria-label={t("modifyNamed", { name: row.label })}
      onClick={(event: MouseEvent<HTMLElement>) => {
        commands?.open({ row, trigger: event.currentTarget });
      }}
    >
      <PencilLine aria-hidden="true" />
      {t("modify")}
    </CellCommand>
  );
}

/** The command that deactivates or reactivates an object from the version read, named after it. */
function ActivationButton({
  target,
  name,
  command,
  conflict,
}: {
  readonly target: ActivationTarget;
  readonly name: string;
  readonly command: "deactivate" | "reactivate";
  readonly conflict: Conflict | undefined;
}) {
  const t = useTranslations("reference.state");
  const said = useTranslations("reference.form");
  const [pending, run] = useRowCommand(
    `${command} ${target.kind} ${target.id}`,
    conflict === undefined ? {} : { [conflict.id]: conflict.name },
  );
  return (
    <CellCommand
      aria-label={t(command, { name })}
      aria-busy={pending}
      onClick={() => {
        run(
          () => setActivation(target, command === "reactivate"),
          (rows) => {
            const own = rows.find((row) => idOf(target.kind, row) === target.id);
            return said(command === "reactivate" ? "reactivated" : "deactivated", {
              name: own?.label ?? name,
              kind: target.kind,
            });
          },
        );
      }}
    >
      {command === "reactivate" ? <RotateCcw aria-hidden="true" /> : <Ban aria-hidden="true" />}
      {t(`${command}Short`)}
    </CellCommand>
  );
}

/**
 * The state of an object in a list — active, or deactivated, said by a mark and a word —, and the
 * command that changes it as the server lists it: available, unavailable with its conditions, or
 * absent. The server lists it only to a session that may modify the function of the object: the front
 * deduces nothing of the permission.
 */
export function StateCell({
  active,
  target,
  name,
  commands,
  conflict,
}: {
  readonly active: boolean;
  readonly target: ActivationTarget;
  readonly name: string;
  /** The commands the server lists on the object (`available_commands`). */
  readonly commands: ReferenceCommands;
  /** The object a refusal of its reactivation may name, as the row knows it. */
  readonly conflict?: Conflict | undefined;
}) {
  const command = active ? "deactivate" : "reactivate";
  const offer = findOffer(commands, command);
  return (
    <span className="inline-flex items-center gap-1.5">
      <ActiveState active={active} />
      {offer === undefined ? null : offer.is_available ? (
        <ActivationButton target={target} name={name} command={command} conflict={conflict} />
      ) : (
        <UnavailableActivation command={command} name={name} offer={offer} />
      )}
    </span>
  );
}
