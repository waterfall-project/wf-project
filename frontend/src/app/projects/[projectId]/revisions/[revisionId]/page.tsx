// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of a revision, last step of the witness path (US-0080): the banner of its reading
 * context (WF-IHM-0020), and the nodes of its main structure, one row each. A project or a
 * revision the API does not find is not found, as at the other screens of a project.
 * Scaffolding without text of its own: EP-02 replaces it with the dense grid and keeps the
 * path.
 */
import { notFound } from "next/navigation";

import { readOrFail } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { readProjectContext } from "@/components/context/reading";
import { type PageSearchParams, pageSearch, readContext } from "@/navigation/context";

/** The route parameters of a revision. */
export interface RevisionParams {
  readonly projectId: string;
  readonly revisionId: string;
}

/**
 * The nodes of the main structure of a revision; none when it has no main structure. A read
 * the API refuses, or cannot answer, is thrown for the pages of the shell to say (`readOrFail`):
 * a grid left empty would say the revision has nothing.
 */
async function mainNodes({ projectId, revisionId }: RevisionParams) {
  const client = serverClient();
  const revision = { project_id: projectId, revision_id: revisionId };
  const structures = await readOrFail("listCostStructures", () =>
    client.GET("/projects/{project_id}/revisions/{revision_id}/structures", {
      params: { path: revision },
    }),
  );
  const main = structures.find((structure) => structure.kind === "main");
  if (main === undefined) {
    return [];
  }
  const nodes = await readOrFail("listNodes", () =>
    client.GET("/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes", {
      params: { path: { ...revision, structure_id: main.structure_id } },
    }),
  );
  return nodes.items;
}

/** Render the nodes of the main structure of a revision. */
export default async function RevisionPage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const pathname = `/projects/${revision.projectId}/revisions/${revision.revisionId}`;
  // An address that names no project or no revision is not found before the API is asked.
  const context = readContext(pathname, pageSearch(search));
  if (context === undefined) {
    notFound();
  }
  const [nodes, read] = await Promise.all([
    mainNodes(revision),
    readProjectContext(pathname, context),
  ]);
  if (read === "not_found") {
    notFound();
  }
  return (
    <>
      <ContextBanner reading={read} />
      <main>
        <table>
          <tbody>
            {nodes.map((node) => (
              <tr key={node.node_id} data-kind={node.kind}>
                <td>{node.row_number}</td>
                <td>{node.task?.label ?? node.estimate_line?.label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </main>
    </>
  );
}
