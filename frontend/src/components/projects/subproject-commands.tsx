// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the sub-projects of a project (FBS-4.2.3, EP-02/L44b): create one, modify one,
 * delete one (WF-PRJ-0050). They follow the command `update` the project lists — the settings of a
 * project are its project managers' (WF-PRJ-0060), and a terminal project lists it unavailable,
 * `project_not_terminal` lacking —: absent, nothing is offered; unavailable, « New sub-project » is
 * presented `aria-disabled`, described by the conditions it lacks; available, the list offers the
 * creation in its head and each row its modification and its deletion. A sub-project charged with
 * actual costs no longer deletes (WF-PRJ-0050): its deletion is presented unavailable, and a press
 * says why in the region of the list, without asking anything. A deletion is confirmed first.
 *
 * The creation and the modification open the form of the reference data (`ReferenceForm`): the code
 * and the label, required, no longer than the contract takes; a code another sub-project bears (409
 * `ALREADY_EXISTS`) is said at its field, its holder named generically — « another sub-project »
 * (EP-02/L42g) —, the form not knowing the rows the list shows. A modification answered takes the
 * place of its row while it is newer than the row read (`lock_version`) — answered for another
 * sub-project, it is a failure of the service (`ANOTHER_OBJECT`), told under the form, and nothing
 * takes the place of any row —, a deletion answered takes its row away, for as long as the screen
 * stays — against the fake back, which keeps nothing (`MockupNotice`) —; a creation adds no row: the
 * page read anew lists the sub-project where the server retains it. What a write did is said in the
 * region of the list; a refusal of a deletion is told above the list (`Reactivations`).
 *
 * The commands of the reference data (`CommandedList`) are bound to its kinds of object: this list has
 * its own, on the same pieces — the form, the command of a cell, the region of the refusals.
 */
"use client";

import { PencilLine, Plus, Trash2 } from "lucide-react";
import { useTranslations } from "next-intl";
import {
  createContext,
  type MouseEvent,
  type ReactNode,
  useContext,
  useId,
  useMemo,
  useState,
  useTransition,
} from "react";

import { deleteSubproject, writeSubproject } from "@/api/actions/projects";
import { UnmetConditions } from "@/components/commands/command";
import { type CommandOffer, UNAVAILABLE, unmetId } from "@/components/commands/offer";
import { rejected } from "@/components/commands/rejection";
import { CELL_COMMAND } from "@/components/grid/grid-keyboard";
import { CellCommand } from "@/components/reference/cell-command";
import { ANOTHER_OBJECT } from "@/components/reference/commands";
import { useListReport } from "@/components/reference/reactivation";
import { ReferenceForm, required } from "@/components/reference/reference-form";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

import type { Subproject } from "./settings-grids";

/** The longest code and label of a sub-project the contract takes. */
const CODE_LENGTH = 50;
const LABEL_LENGTH = 300;

/** A command of a row pressed — its form or its confirmation —, and what opened it. */
interface Opened {
  readonly row: Subproject | undefined;
  readonly trigger: HTMLElement;
  /** Whether it is the deletion of the row, confirmed first, rather than its form. */
  readonly deleting: boolean;
}

/** What the commands of the list hold: the project, what is open, the answers of the server. */
interface Commands {
  readonly project: string;
  readonly opened: Opened | undefined;
  readonly said: { readonly text: string; readonly count: number } | undefined;
  readonly answers: ReadonlyMap<string, Subproject>;
  readonly deleted: ReadonlySet<string>;
  readonly answer: (row: Subproject) => void;
  readonly remove: (id: string) => void;
  readonly say: (text: string) => void;
  readonly open: (opened: Opened | undefined) => void;
}

/** The commands of the list of the sub-projects; none outside it. */
const SubprojectContext = createContext<Commands | undefined>(undefined);

/**
 * The rows of the page, each replaced by the answer of the server to its modification while the
 * answer is newer than the row read, those whose deletion was answered left out.
 */
export function useSubprojectRows(rows: readonly Subproject[]): readonly Subproject[] {
  const commands = useContext(SubprojectContext);
  const answers = commands?.answers;
  const deleted = commands?.deleted;
  // The rows keep their identity while nothing is answered: a dialog opened reads nothing anew.
  return useMemo(() => {
    if (answers === undefined || deleted === undefined || answers.size + deleted.size === 0) {
      return rows;
    }
    return rows
      .filter((row) => !deleted.has(row.subproject_id))
      .map((row) => {
        const answer = answers.get(row.subproject_id);
        return answer !== undefined && answer.lock_version > row.lock_version ? answer : row;
      });
  }, [rows, answers, deleted]);
}

/** The commands of the sub-projects of a project, for the list they hold; none without a project. */
export function SubprojectCommands({
  project,
  children,
}: {
  readonly project: string | undefined;
  readonly children: ReactNode;
}) {
  const [opened, setOpened] = useState<Opened>();
  const [said, setSaid] = useState<Commands["said"]>();
  const [answers, setAnswers] = useState<ReadonlyMap<string, Subproject>>(() => new Map());
  const [deleted, setDeleted] = useState<ReadonlySet<string>>(() => new Set());
  const commands = useMemo<Commands | undefined>(
    () =>
      project === undefined
        ? undefined
        : {
            project,
            opened,
            said,
            answers,
            deleted,
            answer: (row) => {
              setAnswers((before) => {
                const known = before.get(row.subproject_id);
                return known !== undefined && known.lock_version >= row.lock_version
                  ? before
                  : new Map(before).set(row.subproject_id, row);
              });
            },
            remove: (id) => {
              setDeleted((before) => new Set(before).add(id));
            },
            say: (text) => {
              setSaid((before) => ({ text, count: (before?.count ?? 0) + 1 }));
            },
            open: setOpened,
          },
    [project, opened, said, answers, deleted],
  );
  return <SubprojectContext value={commands}>{children}</SubprojectContext>;
}

/**
 * Give the focus back to what opened a form or a confirmation: the cell of the command — the grid
 * being one stop —, or the command; the list when the page read anew no longer holds it.
 */
function focusBack(trigger: HTMLElement, list: (() => void) | undefined) {
  if (!trigger.isConnected) {
    list?.();
    return;
  }
  (trigger.hasAttribute(CELL_COMMAND) ? (trigger.closest("td") ?? trigger) : trigger).focus();
}

/**
 * The head of the list: the region that says what the last write did — or what an unavailable
 * deletion lacks —, rendered from the start so that a reader of the screen hears it; and the command
 * that creates a sub-project, as the project lists `update`.
 */
export function SubprojectHead({ offer }: { readonly offer: CommandOffer | undefined }) {
  const t = useTranslations("projectLists.subprojects");
  const commands = useContext(SubprojectContext);
  const id = useId();
  const said = commands?.said;
  const unmet = offer === undefined ? undefined : unmetId(offer, id);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
        {said === undefined ? null : <span key={said.count}>{said.text}</span>}
      </p>
      {offer === undefined ? null : (
        <>
          <Button
            type="button"
            variant="outline"
            size="sm"
            aria-disabled={offer.is_available ? undefined : true}
            aria-describedby={unmet}
            className={UNAVAILABLE}
            onClick={(event: MouseEvent<HTMLElement>) => {
              if (offer.is_available) {
                commands?.open({ row: undefined, trigger: event.currentTarget, deleting: false });
              }
            }}
          >
            <Plus aria-hidden="true" />
            {t("create")}
          </Button>
          <UnmetConditions id={unmet} offer={offer} />
        </>
      )}
    </div>
  );
}

/** The command that opens the modification of a row, named after its code. */
export function ModifySubproject({ row }: { readonly row: Subproject }) {
  const t = useTranslations("projectLists.subprojects");
  const commands = useContext(SubprojectContext);
  return (
    <CellCommand
      aria-label={t("modifyNamed", { code: row.code })}
      onClick={(event: MouseEvent<HTMLElement>) => {
        commands?.open({ row, trigger: event.currentTarget, deleting: false });
      }}
    >
      <PencilLine aria-hidden="true" />
      {t("modify")}
    </CellCommand>
  );
}

/**
 * The command that deletes a row, named after its code: unavailable once actual costs are charged to
 * it, described by why, a press saying it in the region of the list; available, it opens its
 * confirmation.
 */
export function DeleteSubproject({ row }: { readonly row: Subproject }) {
  const t = useTranslations("projectLists.subprojects");
  const commands = useContext(SubprojectContext);
  const described = `${useId()}-unmet`;
  const charged = row.has_actual_costs;
  return (
    <>
      <CellCommand
        aria-label={t("deleteNamed", { code: row.code })}
        aria-disabled={charged ? true : undefined}
        aria-describedby={charged ? described : undefined}
        className={UNAVAILABLE}
        onClick={(event: MouseEvent<HTMLElement>) => {
          if (charged) {
            commands?.say(t("deleteUnavailable", { code: row.code }));
          } else {
            commands?.open({ row, trigger: event.currentTarget, deleting: true });
          }
        }}
      >
        <Trash2 aria-hidden="true" />
        {t("delete")}
      </CellCommand>
      {charged ? (
        <span id={described} className="sr-only">
          {t("deleteCharged")}
        </span>
      ) : null}
    </>
  );
}

/** The confirmation of the deletion of a sub-project, which asks the API once confirmed. */
function DeleteConfirmation({
  row,
  commands,
  closed,
}: {
  readonly row: Subproject;
  readonly commands: Commands;
  /** Give the focus back where the confirmation was opened from, once it has closed. */
  readonly closed: () => void;
}) {
  const t = useTranslations("projectLists.subprojects");
  const form = useTranslations("reference.form");
  const list = useListReport();
  const [pending, startTransition] = useTransition();
  const confirm = () => {
    if (pending) {
      return;
    }
    // The reading the deletion is confirmed on: its refusal is told on it alone.
    const reading = list?.reading ?? "";
    startTransition(async () => {
      const outcome = await deleteSubproject(commands.project, row.subproject_id).catch(rejected);
      if (outcome.kind === "done") {
        commands.remove(row.subproject_id);
        commands.say(t("deleted", { code: row.code }));
      } else {
        list?.report({
          outcome,
          reading,
          names: { [row.subproject_id]: row.code },
          target: `delete subproject ${row.subproject_id}`,
        });
      }
      commands.open(undefined);
    });
  };
  return (
    <DialogContent
      aria-busy={pending}
      onCloseAutoFocus={(event) => {
        event.preventDefault();
        closed();
      }}
    >
      <DialogHeader>
        <DialogTitle>{t("deleteTitle", { code: row.code })}</DialogTitle>
        <DialogDescription>
          {t("deleteHint", { code: row.code, label: row.label })}
        </DialogDescription>
      </DialogHeader>
      <DialogFooter>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            commands.open(undefined);
          }}
        >
          {form("cancel")}
        </Button>
        <Button type="button" aria-busy={pending} onClick={confirm}>
          <Trash2 aria-hidden="true" />
          {pending ? form("sending") : t("delete")}
        </Button>
      </DialogFooter>
    </DialogContent>
  );
}

/**
 * The form or the confirmation the list has open, rendered within the list, where a refusal answered
 * once it is gone is told; nothing while none is open.
 */
export function SubprojectDialog() {
  const t = useTranslations("projectLists.subprojects");
  const columns = useTranslations("grid.columns");
  const form = useTranslations("reference.form");
  const commands = useContext(SubprojectContext);
  const list = useListReport();
  const opened = commands?.opened;
  if (commands === undefined || opened === undefined) {
    return null;
  }
  const { row, trigger } = opened;
  const close = () => {
    commands.open(undefined);
  };
  const closed = () => {
    focusBack(trigger, list?.refocus);
  };
  if (opened.deleting && row !== undefined) {
    return (
      <Dialog
        open
        onOpenChange={(opened) => {
          if (!opened) {
            close();
          }
        }}
      >
        <DeleteConfirmation row={row} commands={commands} closed={closed} />
      </Dialog>
    );
  }
  return (
    <ReferenceForm<Subproject>
      kind="subproject"
      title={row === undefined ? t("createTitle") : t("modifyNamed", { code: row.code })}
      hint={t("formHint")}
      creating={row === undefined}
      fields={[
        required("code", columns("erpCode"), CODE_LENGTH),
        required("label", columns("label"), LABEL_LENGTH),
      ]}
      initial={row === undefined ? {} : { code: row.code, label: row.label }}
      ask={({ code = "", label = "" }) =>
        writeSubproject(
          commands.project,
          row === undefined
            ? { id: undefined, body: { code, label } }
            : { id: row.subproject_id, body: { code, label, lock_version: row.lock_version } },
        )
      }
      target={row === undefined ? undefined : `modify subproject ${row.subproject_id}`}
      answering={(answer) =>
        row !== undefined &&
        answer.kind === "done" &&
        answer.data.subproject_id !== row.subproject_id
          ? ANOTHER_OBJECT
          : answer
      }
      onDone={(answer) => {
        if (row !== undefined) {
          commands.answer(answer);
        }
        commands.say(
          form(row === undefined ? "created" : "saved", { name: answer.code, kind: "subproject" }),
        );
        close();
      }}
      onClose={close}
      onClosed={closed}
    />
  );
}
