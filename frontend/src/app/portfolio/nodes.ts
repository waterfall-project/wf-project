// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The nodes of organisation a view of the portfolio offers to restrict its labour lines to
 * (WF-PTF-0010), in the order of the tree and each with its depth, as the reference gives them: read by
 * the page of every view whose operation takes a node. The active nodes are read by any session
 * (C-01): the API refuses them to none.
 */
import "server-only";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import type { NodeChoice } from "@/components/portfolio/perimeter";

/** Read the active nodes of organisation, as the server names them. */
export async function readNodes(): Promise<NodeChoice[]> {
  const nodes = await readOrFail("listOrgNodes", () => serverClient().GET("/reference/org-nodes"));
  return nodes.map((node) => ({
    id: node.org_node_id,
    code: node.code,
    label: node.label,
    level: node.level,
  }));
}
