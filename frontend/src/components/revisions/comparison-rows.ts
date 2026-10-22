// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the grid of the comparison of two revisions reads of a node (US-0500, #1201, #1208): the
 * screen asks `compareRevisions` for these fields alone (`fields`) and hands its grid these alone,
 * the server being free to render more than asked — the fake back renders its first example whole.
 * Besides them, a node of a marked tree always bears its identity, its number, its level, its
 * version, and its mark — `difference` and `changes` —, which the server renders whatever `fields`
 * names. No module here is a client one: the page reads the fields, the grid reads the rows.
 */
import type { components } from "@/api/generated/schema";

/** A node of the comparison, as `compareRevisions` renders it. */
type ComparedNode = components["schemas"]["ComparedNodeRead"];

/** The key under which the account keeps the settings of the grid of the comparison. */
export const COMPARISON_KEY = "comparison";

/** The fields of the nodes the grid of the comparison shows, as `fields` names them. */
export const COMPARISON_FIELDS = ["kind", "task.label", "estimate_line.label"] as const;

/** A facet of a node of the comparison as the grid reads it: its label, when the server gave one. */
interface LabelledFacet {
  readonly label?: string;
}

/** A node of the comparison as the grid reads it: its mark, and what its columns show. */
export interface ComparisonRow extends Pick<
  ComparedNode,
  "node_id" | "row_number" | "level" | "lock_version" | "difference" | "changes"
> {
  readonly kind?: components["schemas"]["NodeKind"];
  readonly task?: LabelledFacet | null;
  readonly estimate_line?: LabelledFacet | null;
}

/** A facet reduced to its label: `null` as it came, a label left out as it was. */
function labelled(facet: LabelledFacet | null | undefined): LabelledFacet | null | undefined {
  if (facet === null || facet === undefined) {
    return facet;
  }
  return facet.label === undefined ? {} : { label: facet.label };
}

/** A node of the comparison as the grid reads it, but what the grid does not show. */
export function comparisonRow(node: ComparedNode): ComparisonRow {
  const { node_id, row_number, level, lock_version, difference, changes } = node;
  const task = labelled(node.task);
  const line = labelled(node.estimate_line);
  return {
    node_id,
    row_number,
    level,
    lock_version,
    difference,
    changes,
    ...(node.kind === undefined ? {} : { kind: node.kind }),
    ...(task === undefined ? {} : { task }),
    ...(line === undefined ? {} : { estimate_line: line }),
  };
}

/** The nodes of a comparison as the grid reads them, in the order of the server. */
export function comparisonRows(nodes: readonly ComparedNode[]): ComparisonRow[] {
  return nodes.map(comparisonRow);
}
