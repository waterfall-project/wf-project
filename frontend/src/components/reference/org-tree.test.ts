// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import type { components } from "@/api/generated/schema";
import { example } from "@/test/fixtures";

import { treeLabel } from "./org-tree";

type OrgNode = components["schemas"]["OrgNode"];

describe("the tree of the organisation in a list of choices", () => {
  it("sets each node in by its depth, in the order of the tree the server gives", () => {
    const nodes = example("org_nodes") as OrgNode[];
    expect(nodes.map(treeLabel)).toEqual([
      "Direction technique",
      " Bureau d'études électricité",
      "  Atelier de câblage",
      " Service des achats",
    ]);
  });
});
