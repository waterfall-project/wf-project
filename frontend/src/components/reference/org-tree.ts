// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The tree of the organisation in a list of choices (WF-REF-0070). `listOrgNodes` gives the nodes
 * in the order of the tree — each followed by its descendants, siblings by label — and each with
 * its depth (`level`): a choice sets its name in by that depth, and the list reads as the tree, in
 * the order received. A node is named by its code and its label, as the catalogue joins them
 * (`reference.orgNodes.choice`): two services of the same label, under two parents, stay apart.
 * Nothing is sorted nor nested here.
 */

/** What sets a node in by one level: an em space, which a list of choices does not collapse. */
const INDENT = " ";

/** The name of a node of organisation as a choice, set in by its depth: a root not at all. */
export function treeLabel(level: number, name: string): string {
  return `${INDENT.repeat(Math.max(level - 1, 0))}${name}`;
}
