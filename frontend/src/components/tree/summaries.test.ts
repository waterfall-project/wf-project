// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { NodeList } from "@/components/grid/nodes";
import { example } from "@/test/fixtures";

import { deepest, depthHref, readDepth, summaryTree, type TreeNode } from "./summaries";

// The core of the witness read whole: three summaries at the first level — the studies, the lot
// of the control station, the installation on site —, the subtree the occurrence of a risk merged
// under the lot at the second, and their leaves, milestones and lines below.
const core = (example("nodes_core") as NodeList).items.filter((node) => node.kind === "task");
// A plan of four levels, the counterfactual variant of the witness: the lot of the control station
// ranged under the installation on site, the subtree the occurrence merged a summary of the third
// level, its two tasks at the fourth.
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
  it("shows on a plan of four levels, asked at the second, the summaries of the first two alone, under the root [WF-PLA-0110-A]", () => {
    expect(deepest(nested)).toBe(3);
    expect(labels(summaryTree(nested, 2))).toEqual([
      ["Installation sur site", ["Poste de commande"]],
    ]);
    // The summary of the third level shows once the depth reaches it.
    expect(labels(summaryTree(nested, 3))).toEqual([
      [
        "Installation sur site",
        [["Poste de commande", ["Risque survenu — Retard de livraison des armoires"]]],
      ],
    ]);
  });

  it("shows at a depth the summaries of the levels down to it alone, each under its parent", () => {
    expect(deepest(core)).toBe(2);
    expect(labels(summaryTree(core, 1))).toEqual([
      "Études",
      "Poste de commande",
      "Installation sur site",
    ]);
    expect(labels(summaryTree(core, 2))).toEqual([
      "Études",
      ["Poste de commande", ["Risque survenu — Retard de livraison des armoires"]],
      "Installation sur site",
    ]);
    // Each by the number the API gives it.
    expect(summaryTree(core, 1).map((node) => node.row)).toEqual([1, 8, 19]);
  });

  it("holds no milestone and no leaf, whatever the depth [WF-PLA-0110-A]", () => {
    const shown = JSON.stringify(summaryTree(core, 3));
    for (const absent of ["Réception des études", "Réception usine", "Câblage des armoires"]) {
      expect(shown).not.toContain(absent);
    }
  });

  it("comes down to the project for a plan of leaves alone [WF-PLA-0110-A]", () => {
    const leaves = core.filter((node) => node.task?.is_summary !== true);
    expect(deepest(leaves)).toBe(0);
    expect(summaryTree(leaves, readDepth(search({}), 0))).toEqual([]);
  });

  it("reads its depth in the address, the first two levels when it asks none the tree has", () => {
    expect(readDepth(search({ depth: "1" }), 2)).toBe(1);
    expect(readDepth(search({}), 3)).toBe(2);
    expect(readDepth(search({ depth: "9" }), 3)).toBe(2);
    expect(readDepth(search({ depth: "deep" }), 1)).toBe(1);
    expect(depthHref("/tree", new URLSearchParams({ subproject_id: "s" }), 3)).toBe(
      "/tree?subproject_id=s&depth=3",
    );
  });
});
