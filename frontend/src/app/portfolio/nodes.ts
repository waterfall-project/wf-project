// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The nodes of organisation a view of the portfolio offers to restrict its labour lines to
 * (WF-PTF-0010), each named with its parent as the reference gives them (`parent_label`): read by
 * the page of every view whose operation takes a node. A list the API does not find leaves the
 * view standing, without a node to choose.
 */
import "server-only";

import { readUnlessRefused } from "@/api/problem";
import { serverClient } from "@/api/server";
import type { NodeChoice } from "@/components/portfolio/perimeter";

/**
 * Read the active nodes of organisation, as the server names them; none when it does not find them.
 */
export async function readNodes(): Promise<NodeChoice[]> {
  const nodes = await readUnlessRefused("listOrgNodes", [{ status: 404 }], () =>
    serverClient().GET("/reference/org-nodes"),
  );
  return (nodes ?? []).map((node) => ({
    id: node.org_node_id,
    label: node.label,
    parent: node.parent_label,
  }));
}
