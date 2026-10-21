// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the nodes of a structure — what a computed value depends on
 * (`getComputedValueDependencies`), a cell entered in a grid (`updateTaskFacet`,
 * `updateEstimateLine`, `setLineRemaining`), the predecessors of a task (`setPredecessors`), a
 * task or a line created and a node deleted
 * (`createNode`, `deleteNode`), nodes moved under a task (`moveNodes`), the timelines a task is
 * inscribed to (`setNodeTracking`), a block pasted from a
 * spreadsheet (`previewPaste`, `applyPaste`), the totals of a filtered reading read anew
 * (`listNodes`), the skeleton of the planning generated on an empty main structure
 * (`generatePlanningSkeleton`) —: the grid asks the server of Next,
 * which calls the API (§4.3.1), and gets back the outcome the one decoder makes of its answer
 * (`src/api/problem.ts`).
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

/** What a reading of the nodes asks besides the fields it renders and its sort. */
type NodeFilters = Omit<
  NonNullable<operations["listNodes"]["parameters"]["query"]>,
  "fields" | "sort_by" | "sort_order"
>;

/** The totals of a reading of the nodes, which the server computes. */
type NodeTotals = components["schemas"]["NodeTotals"];

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

/**
 * Re-estimate the line of a node a cell of the grid of the remaining to commit entered — the
 * figure entered alone, from which the server computes the re-estimated amount —, with the version
 * of the node read (WF-RAE-0040): the API answers the node as it now is, with its ancestors and the
 * totals of the structure — or refuses it, on a line of a task completed.
 */
export async function setLineRemaining(
  structure: StructurePath,
  nodeId: string,
  remaining: components["schemas"]["RemainingUpdate"],
): Promise<Outcome<NodesWritten>> {
  return decode(() =>
    serverClient().PUT(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/remaining",
      { ...nodePath(structure, nodeId), body: remaining },
    ),
  );
}

/**
 * Replace the predecessors of the task of a node by those sent, each with the type of its link and its
 * lag in its unit, with the version of the node read (WF-PLA-0030, WF-PLA-0160): the API answers the
 * node as it now is, its ancestors, the tasks the links redate and the totals of the structure — or
 * refuses the links, a loop (`LINK_CYCLE`, its tasks named), a summary linked to one of its
 * subordinates (`LINK_FORBIDDEN`) or a project past its horizon among its reasons; nothing is written
 * then.
 */
export async function setPredecessors(
  structure: StructurePath,
  nodeId: string,
  predecessors: components["schemas"]["PredecessorsReplace"],
): Promise<Outcome<NodesWritten>> {
  return decode(() =>
    serverClient().PUT(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/predecessors",
      { ...nodePath(structure, nodeId), body: predecessors },
    ),
  );
}

/**
 * Replace the inscriptions of the task of a node — the timelines it is inscribed to, and the
 * time/time tracking of a milestone — by those sent, with the version of the node read (WF-PLA-0060):
 * the API answers the node as it now is, with its ancestors and the totals of the structure — or
 * refuses it, a tracking of a task that is no milestone among its reasons (`MILESTONE_REQUIRED`);
 * nothing is written then.
 */
export async function setNodeTracking(
  structure: StructurePath,
  nodeId: string,
  tracking: operations["setNodeTracking"]["requestBody"]["content"]["application/json"],
): Promise<Outcome<NodesWritten>> {
  return decode(() =>
    serverClient().PUT(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}/tracking",
      { ...nodePath(structure, nodeId), body: tracking },
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
 * (WF-IHM-0050): the API writes the valid rows of the plan and not the refused ones, and answers
 * the nodes it wrote, as they now are, with their ancestors, the totals and the version the
 * structure moved on to, and the rows it did not write, each with its reason — those of the
 * preview and those it refuses judging the accepted rows again (`PasteApplied`, EP-14/L42q) —; or
 * it refuses the whole of it, a stale version among its reasons (412).
 */
export async function applyPaste(
  structure: StructurePath,
  confirmation: components["schemas"]["PasteApply"],
): Promise<Outcome<components["schemas"]["PasteApplied"]>> {
  return decode(() =>
    serverClient().POST(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/paste",
      { ...nodesPath(structure), body: confirmation },
    ),
  );
}

/**
 * Create a task or a line of the estimate in the structure of a grid, under the parent and after
 * the node the gesture names (WF-PLA-0130, WF-DEV-0050; #1183): the API answers the node created
 * with its ancestors, the totals of the structure and the version it moved on to — or refuses it,
 * a line under a task completed or a task that takes the project past its horizon among its
 * reasons. The same write from the three grids: which of them may exercise it is the command of
 * the structure read.
 */
export async function createNode(
  structure: StructurePath,
  node: components["schemas"]["NodeCreate"],
): Promise<Outcome<NodesWritten>> {
  return decode(() =>
    serverClient().POST(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes",
      { ...nodesPath(structure), body: node },
    ),
  );
}

/**
 * Delete a node of the structure of a grid (WF-PLA-0070): a task with its lines and its links, a
 * summary with its subordinates too, sent with the counter of the node the grid read
 * (WF-IHM-0110, #1210). The API answers the ancestors recalculated, the totals and the version the
 * structure moved on to — or refuses it, a task already started or bearing an actual cost, or a
 * node written since it was read, among its reasons.
 */
export async function deleteNode(
  structure: StructurePath,
  nodeId: string,
  lockVersion: number,
): Promise<Outcome<NodesWritten>> {
  return decode(() =>
    serverClient().DELETE(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/{node_id}",
      { params: { ...nodePath(structure, nodeId).params, query: { lock_version: lockVersion } } },
    ),
  );
}

/**
 * Move nodes of the structure of a grid under a parent, after the node the gesture names
 * (WF-PLA-0080, WF-PLA-0040; #1183): an indentation is a move under the task above, in the last
 * place, and an outdentation a move after the parent, under the parent of it. The API answers the
 * nodes as they now are, their old and new ancestors recalculated, the tasks redated, the totals and
 * the version the structure moved on to — or refuses it, a link a summary would hold to one of its
 * subordinates (`LINK_FORBIDDEN`), a loop (`LINK_CYCLE`) or a node to follow that is no sibling
 * (`NODE_NOT_SIBLING`) among its reasons; nothing is written then.
 */
export async function moveNodes(
  structure: StructurePath,
  move: components["schemas"]["NodeMove"],
): Promise<Outcome<NodesWritten>> {
  return decode(() =>
    serverClient().POST(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes/move",
      { ...nodesPath(structure), body: move },
    ),
  );
}

/**
 * Read anew the totals of a reading of the nodes a search or a filter narrowed, once its writes
 * answered: the same request as the reading, its filters as they were — the totals the writes
 * answer are those of the whole structure, which a filtered reading reads anew (`NodesWritten`)
 * —, each node asked by its identifier alone, the totals being all the grid takes of it.
 */
export async function readNodeTotals(
  structure: StructurePath,
  filters: NodeFilters,
): Promise<Outcome<NodeTotals>> {
  const outcome = await decode(() =>
    serverClient().GET(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes",
      { params: { path: structure, query: { ...filters, fields: ["node_id"] } } },
    ),
  );
  return outcome.kind === "done" ? { kind: "done", data: outcome.data.totals } : outcome;
}

/**
 * Generate the skeleton of the planning of a revision from the work breakdown of its project, on its
 * main structure still without a task (WF-PRJ-0030): the API answers the tasks it created, as any
 * write of a grid, with the totals and the version the structure moved on to — or refuses it, naming
 * the first condition it lacks (409).
 */
export async function generatePlanningSkeleton(
  projectId: string,
  revisionId: string,
): Promise<Outcome<NodesWritten>> {
  return decode(() =>
    serverClient().POST("/projects/{project_id}/revisions/{revision_id}/skeleton", {
      params: { path: { project_id: projectId, revision_id: revisionId } },
    }),
  );
}
