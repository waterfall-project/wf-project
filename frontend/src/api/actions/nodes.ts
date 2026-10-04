// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the nodes of a structure — what a computed value depends on
 * (`getComputedValueDependencies`), a cell entered in a grid (`updateTaskFacet`,
 * `updateEstimateLine`), a block pasted from a spreadsheet (`previewPaste`, `applyPaste`) —:
 * the grid asks the server of Next, which calls the API (§4.3.1), and gets back the outcome the
 * one decoder makes of its answer (`src/api/problem.ts`).
 */
"use server";

import type { components, operations } from "@/api/generated/schema";
import { decode, type Outcome } from "@/api/problem";
import { serverClient } from "@/api/server";

/** The structure a node lives in: its project, its revision, the structure itself. */
type StructurePath = Omit<
  operations["getComputedValueDependencies"]["parameters"]["path"],
  "node_id"
>;

/** A field whose value the server computes. */
type ComputedValueField = components["schemas"]["ComputedValueField"];

/** What a computed value depends on, as the server says it. */
type ComputedValueDependencies = components["schemas"]["ComputedValueDependencies"];

/**
 * What the API answers a write of a grid with: the nodes written, their ancestors recalculated,
 * the totals of the structure and its version (#188, #201).
 */
type NodesWritten = components["schemas"]["NodesWritten"];

/** The path of a node: its structure, and the node itself. */
function nodePath(structure: StructurePath, nodeId: string) {
  return { params: { path: { ...structure, node_id: nodeId } } };
}

/**
 * Read what the value of a field of a node depends on, once the user tried to enter it
 * (WF-IHM-0030): the rules the server computes it by, and the rows it is drawn from, all named
 * whatever the grid shows of them.
 */
export async function readComputedDependencies(
  structure: StructurePath,
  nodeId: string,
  field: ComputedValueField,
): Promise<Outcome<ComputedValueDependencies>> {
  return decode(() =>
    serverClient().GET(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/dependencies",
      { params: { ...nodePath(structure, nodeId).params, query: { field } } },
    ),
  );
}

/**
 * Write the fields of the task of a node a cell of a grid entered — those alone —, with the
 * version of the node read (WF-IHM-0040): the API answers the node as it now is, its computed
 * values recalculated, with its ancestors and the totals of the structure — or refuses it, a
 * value it computes or a version it no longer has among its reasons.
 */
export async function updateTaskFacet(
  structure: StructurePath,
  nodeId: string,
  task: components["schemas"]["TaskFacetUpdate"],
): Promise<Outcome<NodesWritten>> {
  return decode(() =>
    serverClient().PATCH(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/task",
      { ...nodePath(structure, nodeId), body: task },
    ),
  );
}

/**
 * Write the fields of the line of the estimate of a node a cell of a grid entered — those
 * alone —, with the version of the node read (WF-IHM-0040): the API answers the node as it now
 * is, its amounts recalculated, with its ancestors and the totals of the structure — or refuses
 * it.
 */
export async function updateEstimateLine(
  structure: StructurePath,
  nodeId: string,
  line: components["schemas"]["EstimateLineUpdate"],
): Promise<Outcome<NodesWritten>> {
  return decode(() =>
    serverClient().PATCH(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/estimate-line",
      { ...nodePath(structure, nodeId), body: line },
    ),
  );
}

/** The path of the nodes of a structure, where a block is pasted. */
function nodesPath(structure: StructurePath) {
  return { params: { path: structure } };
}

/**
 * Ask what a block pasted from a spreadsheet would write and refuse, from a cell of a grid
 * (WF-IHM-0050): the API answers its plan — the rows accepted, those refused with their reason —
 * and writes nothing; a block wider than the grid is refused (`PASTE_TOO_WIDE`).
 */
export async function previewPaste(
  structure: StructurePath,
  block: components["schemas"]["PastePreview"],
): Promise<Outcome<components["schemas"]["PastePlan"]>> {
  return decode(() =>
    serverClient().POST(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste-preview",
      { ...nodesPath(structure), body: block },
    ),
  );
}

/**
 * Apply a paste once confirmed, with the version of the structure read, in one operation
 * (WF-IHM-0050): the API answers the nodes it wrote, as they now are, with their ancestors, the
 * totals and the version the structure moved on to — or refuses the whole of it, a stale version
 * among its reasons (412).
 */
export async function applyPaste(
  structure: StructurePath,
  confirmation: components["schemas"]["PasteApply"],
): Promise<Outcome<NodesWritten>> {
  return decode(() =>
    serverClient().POST(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste",
      { ...nodesPath(structure), body: confirmation },
    ),
  );
}
