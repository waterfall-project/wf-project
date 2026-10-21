// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The submenu « Chronologies » of the menu of a cell (US-0480, WF-PLA-0060), and what writes it: a
 * box to check for each timeline of the project — and « Suivi temps/temps » for a milestone. It
 * applies to the rows the menu acts on, the selection the row stands in or the row alone, one write
 * per row with the version of that row; a row that does not name the field it writes among those it
 * accepts is left aside.
 *
 * A project without a timeline offers to create one, named in a dialog, to which the rows are
 * inscribed once it exists.
 */
"use client";

import { CalendarRange, Plus, X } from "lucide-react";
import { useTranslations } from "next-intl";
import { type SubmitEvent, useId, useRef, useState } from "react";

import { setNodeTracking } from "@/api/actions/nodes";
import type { Outcome } from "@/api/problem";
import { UNAVAILABLE } from "@/components/commands/offer";
import { Button } from "@/components/ui/button";
import {
  ContextMenuCheckboxItem,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuSub,
  ContextMenuSubContent,
  ContextMenuSubTrigger,
} from "@/components/ui/context-menu";
import { DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

import type { GridNode, NodesWritten, StructurePath } from "./nodes";
import {
  appliesTo,
  entriesAfter,
  isInscribed,
  milestoneOf,
  type RowChange,
  type RowChoices,
  trackable,
} from "./row-choices";

/** The longest label of a timeline the contract takes. */
const LABEL_LENGTH = 300;

/** What the menu asks of the screen: write a change on the rows, or create a timeline first. */
export interface ChoiceActions<Row extends GridNode> {
  /** Whether a write or its reading anew is under way, which holds the choices. */
  readonly busy: boolean;
  readonly change: (change: RowChange) => void;
  readonly create: () => void;
  readonly row: Row;
}

/** The submenu of the timelines of a task: a box for each, the time/time tracking of a milestone. */
function TimelinesMenu<Row extends GridNode>({
  choices,
  row,
  busy,
  change,
  create,
}: ChoiceActions<Row> & { readonly choices: NonNullable<RowChoices<Row>["tracking"]> }) {
  const t = useTranslations("grid.structure");
  const entries = choices.entries(row);
  const milestone = milestoneOf(row);
  return (
    <ContextMenuSub>
      <ContextMenuSubTrigger aria-disabled={busy ? true : undefined} className={UNAVAILABLE}>
        <CalendarRange aria-hidden="true" />
        {t("timelines")}
      </ContextMenuSubTrigger>
      <ContextMenuSubContent aria-label={t("timelines")} className="max-w-64">
        {choices.timelines.map((timeline) => (
          <ContextMenuCheckboxItem
            key={timeline.id}
            checked={isInscribed(entries, { kind: "timeline", id: timeline.id, on: true })}
            aria-disabled={busy ? true : undefined}
            className={UNAVAILABLE}
            onCheckedChange={(on) => {
              change({ kind: "timeline", id: timeline.id, on });
            }}
          >
            {timeline.label}
          </ContextMenuCheckboxItem>
        ))}
        {milestone ? (
          <ContextMenuCheckboxItem
            checked={isInscribed(entries, { kind: "milestone", on: true })}
            aria-disabled={busy ? true : undefined}
            className={UNAVAILABLE}
            onCheckedChange={(on) => {
              change({ kind: "milestone", on });
            }}
          >
            {t("milestoneTracking")}
          </ContextMenuCheckboxItem>
        ) : null}
        {choices.timelines.length === 0 ? (
          <ContextMenuItem
            aria-disabled={busy ? true : undefined}
            className={UNAVAILABLE}
            onSelect={(event) => {
              if (busy) {
                event.preventDefault();
                return;
              }
              create();
            }}
          >
            <Plus aria-hidden="true" />
            {t("createTimeline")}
          </ContextMenuItem>
        ) : null}
      </ContextMenuSubContent>
    </ContextMenuSub>
  );
}

/**
 * The submenu of the menu of the cell of a row, where the grid gives it and the row names the field
 * it writes: the timelines of a task. Nothing for a row that names none, nor in the menu of the
 * header. `separated` tells that entries come before it.
 */
export function ChoiceMenuItems<Row extends GridNode>({
  choices,
  separated,
  ...actions
}: ChoiceActions<Row> & {
  readonly choices: RowChoices<Row>;
  readonly separated: boolean;
}) {
  const timelines =
    choices.tracking !== undefined && trackable(actions.row) ? choices.tracking : undefined;
  if (timelines === undefined) {
    return null;
  }
  return (
    <>
      {separated ? <ContextMenuSeparator /> : null}
      <TimelinesMenu choices={timelines} {...actions} />
    </>
  );
}

/** The rows a change acts on: those of the selection, or the row alone, that it applies to. */
export function targetsOf<Row extends GridNode>(
  change: RowChange,
  rows: readonly Row[],
): readonly Row[] {
  return rows.filter((row) => appliesTo(change, row));
}

/** What writing a change on the rows told: the outcome, and the row it was refused at. */
export interface ChangeWritten<Row> {
  readonly outcome: Outcome<NodesWritten>;
  readonly at: Row | undefined;
}

/**
 * Write a change on each row in turn, one write per row with the version of that row (`lock_version`),
 * each answer told as it comes. The writes stop at the first refusal, which is told for its row: those
 * made stay made, and the rows after it are left as they were.
 */
export async function writeChange<Row extends GridNode>(
  structure: StructurePath,
  choices: RowChoices<Row>,
  change: RowChange,
  rows: readonly [Row, ...Row[]],
  wrote: (written: NodesWritten) => void,
): Promise<ChangeWritten<Row>> {
  const one = (row: Row): Promise<Outcome<NodesWritten>> =>
    setNodeTracking(structure, row.node_id, {
      entries: [...entriesAfter(choices.tracking?.entries(row) ?? [], change)],
      lock_version: row.lock_version,
    });
  const [first, ...others] = rows;
  let last = await one(first);
  if (last.kind !== "done") {
    return { outcome: last, at: first };
  }
  wrote(last.data);
  for (const row of others) {
    last = await one(row);
    if (last.kind !== "done") {
      return { outcome: last, at: row };
    }
    wrote(last.data);
  }
  return { outcome: last, at: undefined };
}

/** The dialog that names the timeline a task is inscribed to when the project has none. */
export function TimelineForm({
  pending,
  onCreate,
  onCancel,
}: {
  readonly pending: boolean;
  readonly onCreate: (label: string) => void;
  readonly onCancel: () => void;
}) {
  const t = useTranslations("grid.structure");
  const entry = useTranslations("grid.entry");
  const form = useTranslations("reference.form");
  const id = useId();
  const [label, setLabel] = useState("");
  const [empty, setEmpty] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const submit = (event: SubmitEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (pending) {
      return;
    }
    const typed = label.trim();
    if (typed === "") {
      setEmpty(true);
      input.current?.focus();
      return;
    }
    setEmpty(false);
    onCreate(typed);
  };
  return (
    <>
      <DialogHeader>
        <DialogTitle>{t("timelineTitle")}</DialogTitle>
        <DialogDescription>{t("timelineHint")}</DialogDescription>
      </DialogHeader>
      <form aria-label={t("timelineTitle")} noValidate onSubmit={submit} className="grid gap-3">
        <div className="grid gap-1">
          <Label htmlFor={`${id}-label`}>{t("labelField")}</Label>
          <Input
            ref={input}
            id={`${id}-label`}
            value={label}
            maxLength={LABEL_LENGTH}
            aria-required
            aria-invalid={empty ? true : undefined}
            aria-describedby={empty ? `${id}-problem` : undefined}
            onChange={(event) => {
              setLabel(event.target.value);
            }}
          />
          {empty ? (
            <p id={`${id}-problem`} className="text-sm text-destructive">
              {entry("required")}
            </p>
          ) : null}
        </div>
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
