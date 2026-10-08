// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { NodeList } from "@/components/grid/nodes";
import { example } from "@/test/fixtures";

import {
  depthHref,
  depthShown,
  depthsOffered,
  readDepth,
  summaryTree,
  type TreeNode,
} from "./summaries";

// The plan of four levels of the witness asked at the second level (`summaries_only`,
// `max_level=2`), as the server renders it: the studies and the installation on site at the
// first, the lot of the control station ranged under the latter at the second; neither the summary
// of the third level the occurrence merged, nor any leaf, nor any milestone.
const summaries = (example("nodes_summaries") as NodeList).items;
// The subtree of the installation of the same plan read whole, as the fake back renders a reading
// whatever the tree asks: its leaves, its milestones and the summary of the third level too.
const nested = (example("nodes_nested") as NodeList).items;

/** A tree by its labels: each node, and those under it. */
function labels(nodes: readonly TreeNode[]): unknown[] {
  return nodes.map((node) =>
    node.children.length === 0 ? node.label : [node.label, labels(node.children)],
  );
}

/** The address of a query, its parameters given. */
function search(query: Record<string, string>) {
  const parameters = new URLSearchParams(query);
  return { get: (name: string) => parameters.get(name) };
}

describe("the task tree", () => {
  it("hangs the summaries the server renders on a plan of four levels asked at the second each under its parent, under the root [WF-PLA-0110-A]", () => {
    expect(labels(summaryTree(summaries, 2))).toEqual([
      "Études",
      ["Installation sur site", ["Poste de commande"]],
    ]);
    // Each by the number the API gives it, in the order of the answer.
    expect(summaryTree(summaries, 2).map((node) => node.row)).toEqual([1, 8]);
  });

  it("keeps of an answer that holds more the summaries down to the depth asked alone, the same tree a server that filters renders [WF-PLA-0110-A]", () => {
    // Sur un planning de quatre niveaux, l'affichage demandé au niveau 2 ne représente que les
    // récapitulatives des deux premiers niveaux, sous le nœud du projet. Aucun jalon ni aucune
    // tâche feuille n'apparaît, quel que soit le niveau demandé.
    expect(labels(summaryTree(nested, 2))).toEqual([
      ["Installation sur site", ["Poste de commande"]],
    ]);
    const deeper = JSON.stringify(summaryTree(nested, 4));
    expect(deeper).toContain("Risque survenu");
    for (const absent of ["Relance du fournisseur", "Réception usine", "Câblage des armoires"]) {
      expect(deeper).not.toContain(absent);
    }
    // The summary of the third level the answer holds is offered.
    expect(depthsOffered(nested, 2)).toBe(3);
    expect(depthShown(nested, 2)).toBe(2);
  });

  it("hangs under the root a summary whose parent the answer does not hold", () => {
    const [, , lot] = summaries;
    expect(lot === undefined ? [] : labels(summaryTree([lot], 2))).toEqual(["Poste de commande"]);
  });

  it("comes down to the project for a plan without a summary, and offers no depth [WF-PLA-0110-A]", () => {
    expect(summaryTree([], 2)).toEqual([]);
    expect(depthsOffered([], 2)).toBe(0);
  });

  it("offers the depths of the answer, and the next one when a summary is at the depth asked", () => {
    // A summary at the second level asked may have summaries under it: the third is offered.
    expect(depthsOffered(summaries, 2)).toBe(3);
    expect(depthShown(summaries, 2)).toBe(2);
    // Asked deeper than the answer goes, the tree is whole: its deepest level is the one shown.
    expect(depthsOffered(summaries, 3)).toBe(2);
    expect(depthShown(summaries, 3)).toBe(2);
  });

  it("reads its depth in the address, the first two levels when it asks none", () => {
    expect(readDepth(search({ depth: "1" }))).toBe(1);
    expect(readDepth(search({ depth: "9" }))).toBe(9);
    expect(readDepth(search({}))).toBe(2);
    for (const wrong of ["0", "-1", "deep", "2.5", "1e3"]) {
      expect(readDepth(search({ depth: wrong }))).toBe(2);
    }
    expect(depthHref("/tree", new URLSearchParams({ subproject_id: "s" }), 3)).toBe(
      "/tree?subproject_id=s&depth=3",
    );
  });
});
