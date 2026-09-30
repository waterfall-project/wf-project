// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * How a grid of a structure asks what a computed value depends on (WF-IHM-0030): the server
 * action that reads it for a node of the structure, and a field (`getComputedValueDependencies`).
 * The grid names the structure and makes a reader for each reading of it; each computed cell, its
 * node and its field.
 */
import { readComputedDependencies } from "@/api/actions/nodes";

import type { DependencyReader } from "./columns";
import type { GridNode, StructurePath } from "./nodes";

/**
 * The reader of what a computed value of a node of a structure depends on, for one reading of the
 * structure: a grid makes one for each answer it shows.
 */
export function nodeDependencies<Row extends GridNode>(
  structure: StructurePath,
  reading: readonly Row[],
): DependencyReader<Row> {
  return {
    reading: () => reading,
    id: (node) => node.node_id,
    read: (id, field) => readComputedDependencies(structure, id, field),
  };
}
