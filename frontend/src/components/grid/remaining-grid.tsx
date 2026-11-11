// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the remaining to commit in the page: the dense grid — the one component the grids of
 * the planning and of the estimate render too —, given its configuration here, on the side of the
 * browser, where the functions of a configuration live. The page hands it data only: the rows of
 * the answer of `listNodes` as the grid reads them (`projectNodes`), the structure they belong to,
 * what the reading asked of the nodes, whether the remaining to commit may be entered, what the
 * address asked, and the settings the session read. A computed cell asks the server what its value
 * depends on, by the structure and its node; a figure entered is written by the structure and its
 * node too (`setLineRemaining`). What a write answers is read as the grid reads it
 * (`nodesWritten`), but its totals: the reading narrows to the tasks started — the not started
 * too, when asked —, and reads its own totals anew once its writes answered (`readNodeTotals`). Its
 * tree folds as the planning's, the folds kept for the revision.
 */
"use client";

import { useTranslations } from "next-intl";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { readNodeTotals, setLineRemaining } from "@/api/actions/nodes";

import { CompletionDate } from "./completion-date";
import { DenseGrid } from "./dense-grid";
import { OwnLinesOpen } from "./remaining-cells";
import { nodeDependencies } from "./node-dependencies";
import {
  type NodeFilters,
  nodeNarrowing,
  type NodeRows,
  type NodeSortColumn,
  nodesWritten,
  type StructurePath,
} from "./nodes";
import type { GridQuery } from "./query";
import {
  REMAINING_FIELDS,
  needsCompletionDate,
  remainingGrid,
  type RemainingNode,
  type RemainingWrites,
} from "./remaining";
import type { ChoiceOption, RowChoices } from "./row-choices";
import type { GridPreferences } from "./settings";
import { useStructureGestures } from "./structure-gestures";
import { useStructureVersion } from "./structure-version";
import type { LineCategory } from "./structure-rules";

/**
 * What the reading asks that is the scope of the grid, not a filter: the states of the tasks — the
 * started ones, the not started on demand (WF-RAE-0040) —, which unfolds nothing.
 */
const SCOPE = ["progress"] as const;

/**
 * The number of the last date asked, which names the next one (the `key` of its dialog): a counter,
 * not `crypto.randomUUID()`, which a page served over HTTP outside localhost does not have (#2818).
 */
let lastDating = 0;

/** A date asked of the user, which the entry that asked it waits for; `null` gives the entry up. */
interface Dating {
  readonly id: number;
  readonly resolve: (date: string | null) => void;
}

/** What the grid of the remaining to commit shows. */
export interface RemainingGridProps {
  /** The rows of the answer of `listNodes`, as the grid reads them, and its totals. */
  readonly nodes: NodeRows<RemainingNode>;
  /** The structure the rows belong to. */
  readonly structure: StructurePath;
  /** The version of the structure read with the page, which a move of the gestures carries. */
  readonly structureVersion: number;
  /**
   * What the reading asked of the nodes besides their fields and their sort, as it was sent — the
   * states of the tasks always —, whose totals the grid reads anew by the same request.
   */
  readonly filters: NodeFilters;
  /**
   * Whether the remaining to commit may be entered: the main structure read lists `edit_remaining`
   * available to the caller (`GridScreen.commands`). Then the grid places undo and redo too
   * (US-0140); otherwise it is read only.
   */
  readonly editable: boolean;
  /** The categories of expense a line is created from; with no role, none, and no line is created. */
  readonly categories?: readonly LineCategory[] | undefined;
  /** The roles a line of labour is created from. */
  readonly roles?: readonly LineCategory[] | undefined;
  /**
   * The sub-projects of the project, which the menu of the cells of a line offers it (US-0480): a
   * line is carried to one from the remaining to commit once the project is in progress; none, and
   * the grid offers no submenu.
   */
  readonly subprojects?: readonly ChoiceOption[] | undefined;
  readonly query: GridQuery<NodeSortColumn>;
  readonly preferences: GridPreferences | undefined;
}

/**
 * How the grid re-estimates a line: the figure entered and the version of the node read
 * (`lock_version`), nothing else — the answer read as the grid reads it. The reading always
 * narrows to some states of the tasks (`progress`): its totals are never those of the structure a
 * write answers, and are read anew by the same request.
 */
function structureWrites(
  structure: StructurePath,
  filters: NodeFilters,
  reach: (version: number) => void,
  askDate: () => Promise<string | null>,
): RemainingWrites {
  return {
    totals: () => readNodeTotals(structure, filters),
    line: async (node, basis) => {
      const send = (completedOn?: string) =>
        setLineRemaining(structure, node.node_id, {
          reestimated_amount_basis: basis,
          lock_version: node.lock_version,
          ...(completedOn === undefined ? {} : { completed_on: completedOn }),
        });
      let outcome = await send();
      // The entry completes the task: nothing was written, the date is asked and the entry replayed
      // from the same version; given up, the refusal is told at the cell (WF-RAE-0040).
      if (needsCompletionDate(outcome)) {
        const date = await askDate();
        if (date !== null) {
          outcome = await send(date);
        }
      }
      if (outcome.kind !== "done") {
        return outcome;
      }
      reach(outcome.data.structure_lock_version);
      return { kind: "done", data: nodesWritten(outcome.data, REMAINING_FIELDS, false) };
    },
  };
}

/** Render the grid of the remaining to commit, its totals counting the tasks and lines retained. */
export function RemainingGrid({
  nodes,
  structure,
  structureVersion,
  filters,
  editable,
  categories,
  roles,
  subprojects,
  query,
  preferences,
}: RemainingGridProps) {
  const t = useTranslations("estimateGrid");
  // A reader for each reading: an answer names rows a new reading may have renumbered.
  const dependencies = useMemo(
    () => nodeDependencies(structure, nodes.items),
    [structure, nodes.items],
  );
  const account = useStructureVersion(structure.structure_id, structureVersion);
  const { version, reach } = account;
  // The reading always narrows to some states of the tasks: the totals of the structure a write
  // answers are never its own.
  const choices = useMemo<RowChoices<RemainingNode> | undefined>(
    () =>
      !editable || subprojects === undefined
        ? undefined
        : {
            subproject: {
              subprojects,
              current: (node) => node.estimate_line?.subproject_id ?? null,
            },
            written: (written) => nodesWritten(written, REMAINING_FIELDS, false),
          },
    [editable, subprojects],
  );
  const gestures = useStructureGestures<RemainingNode>(
    editable
      ? {
          structure,
          tasks: true,
          lines: true,
          categories,
          roles,
          rows: nodes.items,
          version,
        }
      : undefined,
    account,
    choices,
  );
  // The dates a re-estimation that completes a task asks, one dialog at a time, in the order asked:
  // the writes of two rows may ask together, and a grid gone gives up the dates asked.
  const [asking, setAsking] = useState<readonly Dating[]>([]);
  const askDate = useCallback(
    () =>
      new Promise<string | null>((resolve) => {
        setAsking((before) => [...before, { id: (lastDating += 1), resolve }]);
      }),
    [],
  );
  // What the grid gone still asks is given up, or its writes would wait for ever.
  const unanswered = useRef(asking);
  useEffect(() => {
    unanswered.current = asking;
  });
  useEffect(
    () => () => {
      for (const dating of unanswered.current) {
        dating.resolve(null);
      }
    },
    [],
  );
  const config = useMemo(
    () => remainingGrid(editable ? structureWrites(structure, filters, reach, askDate) : undefined),
    [editable, structure, filters, reach, askDate],
  );
  const [first] = asking;
  return (
    <>
      {first === undefined ? null : (
        <CompletionDate
          key={first.id}
          onAnswer={(date) => {
            setAsking((before) => before.filter((dating) => dating !== first));
            first.resolve(date);
          }}
        />
      )}
      <DenseGrid
        config={config}
        rows={nodes.items}
        totals={nodes.totals}
        totalsCaption={(totals) =>
          t("totals", { tasks: totals.task_count, lines: totals.estimate_line_count })
        }
        query={query}
        preferences={preferences}
        dependencies={dependencies}
        foldScope={structure.revision_id}
        narrowing={nodeNarrowing(filters, SCOPE)}
        undoable={editable}
        commands={gestures}
        around={(rows, grid) => <OwnLinesOpen rows={rows}>{grid}</OwnLinesOpen>}
      />
    </>
  );
}
