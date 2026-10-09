// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The commands of the natures and the categories of cost (FBS-3.1.1, EP-02/L43a): create one, modify
 * one, deactivate or reactivate one — none deletes it, the reference data deactivating rather than
 * deleting (WF-REF-0010, WF-DAT-0080). The creation and the modification follow the permission of
 * modification of the cost settings (`platformOffer`): the page offers them to a session that holds
 * it, and to no other (WF-IHM-0090); the activation follows the command each object lists
 * (`available_commands`), absent, available, or unavailable with the conditions it lacks.
 *
 * Each list has its commands (`CostCommands`): the form they open (`CostForm`, rendered in the list
 * by `CostDialog`), one at a time, and the answers of the server to the writes of its rows. Every
 * write answered reads the page anew (`readAnew` of the server actions) — the natures are what the
 * categories are filtered on and attached to —; a modification or an activation answered takes the
 * place of its row meanwhile, as long as the answer is newer than the row the page read
 * (`lock_version`), a reading that has caught up prevailing. Against the fake back, which keeps
 * nothing, a row answered so outlives the readings anew, which serve what it served before
 * (`MockupNotice`). A creation adds no row: the page read anew lists the object where the server
 * retains it. What a write did is said in the region of the list, the dialog open or closed; a refusal
 * answered once the dialog is gone, and the refusal of an activation, are said above the list as that
 * of a reactivation (`useListReport`). A dialog closed gives the focus back where it was opened from:
 * the cell of the row, the grid being one stop, or the command of the creation.
 *
 * Every prop a server component hands is data — the kind of the list, the natures to choose from —,
 * never a function (défaut n° 12 de `typescript.md`). In a dense grid, a command is out of the order
 * of tabulation, the grid being one stop: Enter on its cell presses it (`CELL_COMMAND`).
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

import { setCostActivation } from "@/api/actions/reference";
import { findOffer } from "@/components/commands/offer";
import { rejected } from "@/components/commands/rejection";
import { CELL_COMMAND } from "@/components/grid/grid-keyboard";
import { Button } from "@/components/ui/button";

import { CostForm } from "./cost-form";
import { type CostObject, idOf, type NatureChoice } from "./cost-kinds";
import { UnavailableActivation, useListReport } from "./reactivation";
import { ActiveState } from "./section";

/** The kind of the objects a list of the settings of the costs holds. */
export type CostKind = "cost_type" | "cost_category";

/** The form a list has open: a creation, or the modification of a row, and what opened it. */
interface Opened {
  readonly row: CostObject | undefined;
  /** The command pressed, which the focus goes back to — or its cell — once the dialog has closed. */
  readonly trigger: HTMLElement;
}

/** What a write of a list did, said in its region, and the how-many-th it was. */
interface Said {
  readonly text: string;
  readonly count: number;
}

/** The commands of a list, its form open, and the answers of the server to the writes of its rows. */
interface Commands {
  readonly kind: CostKind;
  readonly natures: readonly NatureChoice[];
  readonly opened: Opened | undefined;
  readonly said: Said | undefined;
  readonly answers: ReadonlyMap<string, CostObject>;
  /** Take the answer of the server to a write of a row: the newest of its answers prevails. */
  readonly answer: (row: CostObject) => void;
  readonly say: (text: string) => void;
  readonly open: (opened: Opened) => void;
  /** Close the form of an opening, if it is still the one open. */
  readonly close: (opened: Opened) => void;
}

/** The commands of the list that holds them; none outside a list of the settings of the costs. */
const ListCommands = createContext<Commands | undefined>(undefined);

/**
 * The rows of a page, each replaced by the answer of the server to a write of it while the answer is
 * newer than the row read — against the fake back, which keeps nothing, for as long as the screen
 * stays.
 */
export function useAnswered<Row extends CostObject>(rows: readonly Row[]): readonly Row[] {
  const answers = useContext(ListCommands)?.answers;
  return useMemo(() => {
    if (answers === undefined || answers.size === 0) {
      return rows;
    }
    return rows.map((row) => {
      const answer = answers.get(idOf(row));
      // A list holds its own kind of object alone: the answer to a row is of the row's kind.
      return answer !== undefined && answer.lock_version > row.lock_version ? (answer as Row) : row;
    });
  }, [rows, answers]);
}

/**
 * Give the focus back to what opened a form: the cell of a command of a row, or the command — the list
 * when the page read anew no longer holds it.
 */
function focusBack({ trigger }: Opened, list: (() => void) | undefined) {
  if (!trigger.isConnected) {
    list?.();
    return;
  }
  const cell = trigger.hasAttribute(CELL_COMMAND) ? trigger.closest<HTMLElement>("td") : null;
  (cell ?? trigger).focus();
}

/**
 * The commands of a list of natures or of categories: its form, the region that says what a write
 * did, and the answers of the server to the writes of its rows.
 */
export function CostCommands({
  kind,
  natures,
  children,
}: {
  readonly kind: CostKind;
  /** The natures a category may be attached to, in the order of the server; none for the natures. */
  readonly natures: readonly NatureChoice[];
  readonly children: ReactNode;
}) {
  const [answers, setAnswers] = useState<ReadonlyMap<string, CostObject>>(() => new Map());
  const [opened, setOpened] = useState<Opened>();
  const [said, setSaid] = useState<Said>();
  const commands = useMemo<Commands>(
    () => ({
      kind,
      natures,
      opened,
      said,
      answers,
      answer: (row) => {
        setAnswers((before) => {
          const known = before.get(idOf(row));
          return known !== undefined && known.lock_version >= row.lock_version
            ? before
            : new Map(before).set(idOf(row), row);
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
    [kind, natures, opened, said, answers],
  );
  return <ListCommands value={commands}>{children}</ListCommands>;
}

/**
 * The form of the list, open as its commands ask, rendered within the list, where a refusal answered
 * once the dialog is gone is told (`useListReport`).
 */
export function CostDialog() {
  const t = useTranslations("reference.costForm");
  const commands = useContext(ListCommands);
  const list = useListReport();
  const opened = commands?.opened;
  if (commands === undefined || opened === undefined) {
    return null;
  }
  const created = opened.row === undefined;
  return (
    <CostForm
      kind={commands.kind}
      row={opened.row}
      natures={commands.natures}
      onDone={(answer) => {
        if (!created) {
          commands.answer(answer);
        }
        commands.say(t(created ? "created" : "saved", { name: answer.label }));
        commands.close(opened);
      }}
      onClose={() => {
        commands.close(opened);
      }}
      onClosed={() => {
        focusBack(opened, list?.refocus);
      }}
    />
  );
}

/**
 * The region that says what the last write of the list did, rendered from the start so that a reader
 * of the screen hears what is put in it, and taking no room while it says nothing.
 */
function CostWritten() {
  const said = useContext(ListCommands)?.said;
  return (
    <p role="status" aria-live="polite" className="text-sm text-muted-foreground empty:sr-only">
      {said === undefined ? null : <span key={said.count}>{said.text}</span>}
    </p>
  );
}

/**
 * The command that opens the creation of a nature or a category, in the head of the list that holds
 * it — offered on an empty list too —, after the region that says what the last write of the list did.
 */
export function CreateCostCommand({ kind }: { readonly kind: CostKind }) {
  const t = useTranslations("reference");
  const commands = useContext(ListCommands);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <CostWritten />
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={(event: MouseEvent<HTMLElement>) => {
          commands?.open({ row: undefined, trigger: event.currentTarget });
        }}
      >
        <Plus aria-hidden="true" />
        {t(kind === "cost_type" ? "costTypes.create" : "costCategories.create")}
      </Button>
    </div>
  );
}

/** The command that opens the modification of a row, named after it. */
export function ModifyCostCommand({ row }: { readonly row: CostObject }) {
  const t = useTranslations("reference");
  const commands = useContext(ListCommands);
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      tabIndex={-1}
      {...{ [CELL_COMMAND]: "" }}
      aria-label={t("modifyNamed", { name: row.label })}
      className="h-5 px-1.5 text-xs"
      onClick={(event: MouseEvent<HTMLElement>) => {
        commands?.open({ row, trigger: event.currentTarget });
      }}
    >
      <PencilLine aria-hidden="true" />
      {t("modify")}
    </Button>
  );
}

/** The command that deactivates or reactivates a row from the version read, named after it. */
function ActivationButton({
  row,
  command,
}: {
  readonly row: CostObject;
  readonly command: "deactivate" | "reactivate";
}) {
  const t = useTranslations("reference.state");
  const said = useTranslations("reference.costForm");
  const list = useListReport();
  const commands = useContext(ListCommands);
  const [pending, startTransition] = useTransition();
  const run = () => {
    if (pending) {
      return;
    }
    // The reading the command is pressed on: its refusal is told on it alone.
    const reading = list?.reading ?? "";
    const target = {
      kind: "cost_category_id" in row ? "cost_category" : "cost_type",
      id: idOf(row),
      lockVersion: row.lock_version,
    } as const;
    startTransition(async () => {
      const outcome = await setCostActivation(target, command === "reactivate").catch(rejected);
      if (outcome.kind === "done") {
        commands?.answer(outcome.data);
        commands?.say(
          said(outcome.data.is_active ? "reactivated" : "deactivated", {
            name: outcome.data.label,
          }),
        );
      } else {
        list?.report({
          outcome,
          reading,
          names: {},
          target: `${command} ${target.kind} ${target.id}`,
        });
      }
    });
  };
  return (
    <Button
      type="button"
      variant="outline"
      size="sm"
      tabIndex={-1}
      {...{ [CELL_COMMAND]: "" }}
      aria-label={t(command, { name: row.label })}
      aria-busy={pending}
      className="h-5 px-1.5 text-xs"
      onClick={run}
    >
      {command === "reactivate" ? <RotateCcw aria-hidden="true" /> : <Ban aria-hidden="true" />}
      {t(`${command}Short`)}
    </Button>
  );
}

/**
 * The state of a nature or a category — active, or deactivated said by a mark and a word —, and the
 * command that changes it as the object lists it: available, unavailable with its conditions, or
 * absent.
 */
export function CostStateCell({ row }: { readonly row: CostObject }) {
  const command = row.is_active ? "deactivate" : "reactivate";
  const offer = findOffer(row.available_commands, command);
  return (
    <span className="inline-flex items-center gap-1.5">
      <ActiveState active={row.is_active} />
      {offer === undefined ? null : offer.is_available ? (
        <ActivationButton row={row} command={command} />
      ) : (
        <UnavailableActivation command={command} name={row.label} offer={offer} />
      )}
    </span>
  );
}
