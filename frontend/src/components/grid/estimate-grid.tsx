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
 * structure and its node; a cell entered is written by the structure and its node too, the node
 * answered read as the grid reads it; a block pasted, by the structure and the version read of it,
 * the nodes answered read as the grid reads them.
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo, useState } from "react";

import { applyPaste, previewPaste, updateEstimateLine, updateTaskFacet } from "@/api/actions/nodes";
import type { Outcome } from "@/api/problem";

import { DenseGrid } from "./dense-grid";
import {
  ESTIMATE_FIELDS,
  estimateGrid,
  type EstimateNode,
  type EstimateReference,
  type EstimateWrites,
} from "./estimate";
import { nodeDependencies } from "./node-dependencies";
import {
  type NodeRows,
  type NodesWritten,
  type NodeSortColumn,
  projectNode,
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

/** Told the version the structure moved on to, which the next paste carries. */
type Moved = (version: number) => void;

/**
 * The nodes the API answered a write with, as the grid of the estimate reads them; the version the
 * structure moved on to is told, for the next paste. The ancestors and the totals the answer
 * carries too are not applied yet (#218).
 */
function asRows(outcome: Outcome<NodesWritten>, moved: Moved): Outcome<readonly EstimateNode[]> {
  if (outcome.kind !== "done") {
    return outcome;
  }
  moved(outcome.data.structure_lock_version);
  return {
    kind: "done",
    data: outcome.data.nodes.map((node) => projectNode(node, ESTIMATE_FIELDS)),
  };
}

/** The one node a write of a cell answers, as the grid of the estimate reads it. */
function asRow(outcome: Outcome<NodesWritten>, moved: Moved): Outcome<EstimateNode> {
  const rows = asRows(outcome, moved);
  if (rows.kind !== "done") {
    return rows;
  }
  const [row] = rows.data;
  if (row === undefined) {
    throw new Error("a write of a cell answered no node");
  }
  return { kind: "done", data: row };
}

/**
 * How the grid pastes a block in the structure: from the node of the active cell and its column,
 * under the name of its column in the contract (#200); the plan confirmed, with the version of
 * the structure last read or answered (#201).
 */
function structurePaste(
  structure: StructurePath,
  version: number,
  moved: Moved,
): EstimateWrites["paste"] {
  return {
    preview: (node, column, block) =>
      previewPaste(structure, {
        target_node_id: node.node_id,
        target_column: column,
        rows: block.map((cells) => [...cells]),
      }),
    apply: async (plan) =>
      asRows(
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
 * only where the planning may be entered.
 */
function structureWrites(
  structure: StructurePath,
  version: number,
  moved: Moved,
  tasks: boolean,
): EstimateWrites {
  return {
    paste: structurePaste(structure, version, moved),
    line: async (node, change) =>
      asRow(
        await updateEstimateLine(structure, node.node_id, {
          ...change,
          lock_version: node.lock_version,
        }),
        moved,
      ),
    task: tasks
      ? async (node, label) =>
          asRow(
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
  reference,
  editable,
  tasksEditable,
  query,
  preferences,
}: EstimateGridProps) {
  const t = useTranslations("estimateGrid");
  const unknown = useTranslations("grid")("unknown");
  // The version of the structure moves with each write answered: the last one told, or the one
  // read with the page when a new reading is more recent.
  const [moved, setMoved] = useState(structureVersion);
  const version = Math.max(structureVersion, moved);
  // A reader for each reading: an answer names rows a new reading may have renumbered.
  const dependencies = useMemo(
    () => nodeDependencies(structure, nodes.items),
    [structure, nodes.items],
  );
  const config = useMemo(
    () =>
      estimateGrid(
        reference,
        unknown,
        editable ? structureWrites(structure, version, setMoved, tasksEditable) : undefined,
      ),
    [reference, unknown, editable, tasksEditable, structure, version],
  );
  return (
    <DenseGrid
      config={config}
      rows={nodes.items}
      totals={nodes.totals}
      totalsCaption={t("totals", {
        tasks: nodes.totals.task_count,
        lines: nodes.totals.estimate_line_count,
      })}
      query={query}
      preferences={preferences}
      dependencies={dependencies}
    />
  );
}
