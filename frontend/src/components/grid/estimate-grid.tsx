// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the estimate in the page: the dense grid — the one component the grid of the
 * planning renders too —, given its configuration here, on the side of the browser — a
 * configuration reads the rows by functions, which never cross from a server component to a
 * client one. The page hands it data only: the rows of the answer of `listNodes` as the grid
 * reads them (`projectNodes`), the structure they belong to, the categories and roles that name
 * those of the lines, whether the revision may be entered, what the address asked, and the
 * settings the session read. A computed cell asks the server what its value depends on, by the
 * structure and its node; a cell entered is written by the structure and its node too; a block
 * pasted, by the structure and the version read of it. What a write answers — the nodes written,
 * the ancestors recalculated, the tasks rescheduled, the totals of the structure — is read as the
 * grid reads it (`nodesWritten`, #218), the totals taken only by a grid read without a search nor
 * a filter, whose totals are those of the structure; a grid read with either reads its own anew by
 * the same request, once its writes answered (`readNodeTotals`).
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import {
  applyPaste,
  previewPaste,
  readNodeTotals,
  updateEstimateLine,
  updateTaskFacet,
} from "@/api/actions/nodes";
import type { Outcome } from "@/api/problem";

import { DenseGrid } from "./dense-grid";
import {
  ESTIMATE_FIELDS,
  estimateGrid,
  type EstimateNode,
  type EstimateReference,
  type EstimateWrites,
  type EstimateWritten,
} from "./estimate";
import { nodeDependencies } from "./node-dependencies";
import {
  type NodeColumn,
  type NodeFilters,
  type NodeRows,
  type NodesWritten,
  type NodeSortColumn,
  nodesWritten,
  pasteSpan,
  type StructurePath,
} from "./nodes";
import type { GridQuery } from "./query";
import type { GridPreferences } from "./settings";

/** What the grid of the estimate shows. */
export interface EstimateGridProps {
  /** The rows of the answer of `listNodes`, as the grid reads them, and its totals. */
  readonly nodes: NodeRows<EstimateNode>;
  /** The structure the rows belong to. */
  readonly structure: StructurePath;
  /**
   * The version of the structure read with the page, which a paste applied carries and every write
   * of the grid moves on (`NodesWritten.structure_lock_version`, #201).
   */
  readonly structureVersion: number;
  /**
   * What the reading asked of the nodes besides their fields and their sort, as it was sent: one
   * that asks a search or a filter — a sub-project — has totals of its own, which those of the
   * structure a write answers are not, and which the grid reads anew by the same request.
   */
  readonly filters: NodeFilters;
  /** The categories and roles the lines are named by, and chosen from. */
  readonly reference: EstimateReference;
  /**
   * Whether the estimate may be entered: the revision is open and lists `edit_estimate` available
   * to the caller (`availableEdits`). Otherwise the grid is read only, and offers no entry the
   * API would refuse.
   */
  readonly editable: boolean;
  /**
   * Whether the label of a task may be entered too: it is the planning's (`updateTaskFacet`), which
   * the revision lists as `edit_planning`.
   */
  readonly tasksEditable: boolean;
  readonly query: GridQuery<NodeSortColumn>;
  readonly preferences: GridPreferences | undefined;
}

/**
 * Told what a write answered: the version the structure moved on to, which the next paste
 * carries; and whether the grid reads the structure whole, whose totals it takes.
 */
interface Moved {
  readonly to: (version: number) => void;
  readonly whole: boolean;
}

/**
 * What the API answered a write with, as the grid of the estimate reads it; the version the
 * structure moved on to is told, for the next paste.
 */
function asWritten(outcome: Outcome<NodesWritten>, moved: Moved): Outcome<EstimateWritten> {
  if (outcome.kind !== "done") {
    return outcome;
  }
  moved.to(outcome.data.structure_lock_version);
  return { kind: "done", data: nodesWritten(outcome.data, ESTIMATE_FIELDS, moved.whole) };
}

/**
 * How the grid pastes a block in the structure: from the node of the active cell and its column,
 * under the name of its column in the contract (#200), the block measured on the columns of the
 * facet of the node (#223); the plan confirmed, with the version of the structure last read or
 * answered (#201).
 */
function structurePaste(
  structure: StructurePath,
  version: number,
  moved: Moved,
  name: (column: NodeColumn) => string,
): EstimateWrites["paste"] {
  return {
    span: pasteSpan,
    name,
    preview: (node, column, block) =>
      previewPaste(structure, {
        target_node_id: node.node_id,
        target_column: column,
        rows: block.map((cells) => [...cells]),
      }),
    apply: async (plan) =>
      asWritten(
        await applyPaste(structure, {
          paste_id: plan.paste_id,
          confirmed: true,
          lock_version: version,
        }),
        moved,
      ),
  };
}

/**
 * How the grid writes the cells of a structure: each write carries the field entered and the
 * version of the node read (`lock_version`), nothing else (#178). The label of a task is written
 * only where the planning may be entered. A reading narrowed by a search or a filter reads its
 * totals anew by its own request, which the writes do not answer.
 */
function structureWrites(
  structure: StructurePath,
  version: number,
  moved: Moved,
  tasks: boolean,
  name: (column: NodeColumn) => string,
  filters: NodeFilters,
): EstimateWrites {
  return {
    paste: structurePaste(structure, version, moved, name),
    totals: moved.whole ? undefined : () => readNodeTotals(structure, filters),
    line: async (node, change) =>
      asWritten(
        await updateEstimateLine(structure, node.node_id, {
          ...change,
          lock_version: node.lock_version,
        }),
        moved,
      ),
    task: tasks
      ? async (node, label) =>
          asWritten(
            await updateTaskFacet(structure, node.node_id, {
              label,
              lock_version: node.lock_version,
            }),
            moved,
          )
      : undefined,
  };
}

/** Render the grid of the estimate, its totals counting the tasks and the lines retained. */
export function EstimateGrid({
  nodes,
  structure,
  structureVersion,
  filters,
  reference,
  editable,
  tasksEditable,
  query,
  preferences,
}: EstimateGridProps) {
  const t = useTranslations("estimateGrid");
  const unknown = useTranslations("grid")("unknown");
  const columns = useTranslations("enums.NodeColumn");
  // The version of the structure moves with each write answered: the highest one told — writes
  // of different rows leave together, and an answer may come back after a later one —, or the
  // one read with the page when a new reading is more recent.
  const [moved, setMoved] = useState(structureVersion);
  const version = Math.max(structureVersion, moved);
  // A reader for each reading: an answer names rows a new reading may have renumbered.
  const dependencies = useMemo(
    () => nodeDependencies(structure, nodes.items),
    [structure, nodes.items],
  );
  const config = useMemo(() => {
    const told: Moved = {
      to: (next) => {
        setMoved((before) => Math.max(before, next));
      },
      // A reading that asks nothing but its fields and its sort is the whole structure.
      whole: Object.keys(filters).length === 0,
    };
    const name = (column: NodeColumn) => columns(column);
    return estimateGrid(
      reference,
      unknown,
      editable
        ? structureWrites(structure, version, told, tasksEditable, name, filters)
        : undefined,
    );
  }, [reference, unknown, editable, tasksEditable, structure, version, filters, columns]);
  return (
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
    />
  );
}
