// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the estimate in the page: the dense grid — the one component the grid of the
 * planning renders too —, given its configuration here, on the side of the browser — a
 * configuration reads the rows by functions, which never cross from a server component to a
 * client one. The page hands it data only: the rows of the answer of `listNodes` as the grid
 * reads them (`projectNodes`), the structure they belong to, whether the revision may be entered,
 * what the address asked, and the settings the session read. A computed cell asks the server what its value depends on, by the
 * structure and its node; a cell of a line entered is written by the structure and its node too,
 * the node answered read as the grid reads it.
 */
"use client";

import { useTranslations } from "next-intl";
import { useMemo } from "react";

import { updateEstimateLine } from "@/api/actions/nodes";
import type { Outcome } from "@/api/problem";

import { DenseGrid } from "./dense-grid";
import { ESTIMATE_FIELDS, estimateGrid, type EstimateNode, type EstimateWrites } from "./estimate";
import { nodeDependencies } from "./node-dependencies";
import {
  type Node,
  type NodeRows,
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
   * Whether the estimate may be entered: the revision is open and lists `edit_estimate` available
   * to the caller (`availableEdits`). Otherwise the grid is read only, and offers no entry the
   * API would refuse.
   */
  readonly editable: boolean;
  readonly query: GridQuery<NodeSortColumn>;
  readonly preferences: GridPreferences | undefined;
}

/** A node the API answered, as the grid of the estimate reads it. */
function asRow(outcome: Outcome<Node>): Outcome<EstimateNode> {
  return outcome.kind === "done"
    ? { kind: "done", data: projectNode(outcome.data, ESTIMATE_FIELDS) }
    : outcome;
}

/**
 * How the grid writes the cells of a structure: each write carries what the contract requires —
 * the label, the category and the quantity of a line (#178) — and the version of the node read
 * (`lock_version`), with the field entered.
 */
function structureWrites(structure: StructurePath): EstimateWrites {
  return {
    line: async (node, change) => {
      const line = node.estimate_line;
      const required = {
        label: line?.label ?? "",
        cost_category_id: line?.cost_category_id ?? "",
        quantity: line?.quantity ?? "",
      };
      const body = { ...required, ...change, lock_version: node.lock_version };
      return asRow(await updateEstimateLine(structure, node.node_id, body));
    },
  };
}

/** Render the grid of the estimate, its totals counting the tasks and the lines retained. */
export function EstimateGrid({
  nodes,
  structure,
  editable,
  query,
  preferences,
}: EstimateGridProps) {
  const t = useTranslations("estimateGrid");
  // A reader for each reading: an answer names rows a new reading may have renumbered.
  const dependencies = useMemo(
    () => nodeDependencies(structure, nodes.items),
    [structure, nodes.items],
  );
  const config = useMemo(
    () => estimateGrid(editable ? structureWrites(structure) : undefined),
    [editable, structure],
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
