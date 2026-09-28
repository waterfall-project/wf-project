// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of a revision, last step of the witness path (US-0080): the banner of its reading
 * context (WF-IHM-0020), and the nodes of its main structure, one row each. Scaffolding
 * without text of its own: EP-02 replaces it with the dense grid and keeps the path.
 */
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { readAddress } from "@/components/context/reading";
import { type PageSearchParams, pageSearch } from "@/navigation/context";

/** The route parameters of a revision. */
export interface RevisionParams {
  readonly projectId: string;
  readonly revisionId: string;
}

/** The nodes of the main structure of a revision, when it has one. */
async function mainNodes({ projectId, revisionId }: RevisionParams) {
  const client = serverClient();
  const revision = { project_id: projectId, revision_id: revisionId };
  const structures = await client.GET("/projects/{project_id}/revisions/{revision_id}/structures", {
    params: { path: revision },
  });
  const main = structures.data?.find((structure) => structure.kind === "main");
  const nodes = main
    ? await client.GET(
        "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes",
        { params: { path: { ...revision, structure_id: main.structure_id } } },
      )
    : undefined;
  return nodes?.data?.items;
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
  const [nodes, read] = await Promise.all([
    mainNodes(revision),
    readAddress(pathname, pageSearch(search)),
  ]);
  return (
    <>
      {typeof read === "object" ? <ContextBanner reading={read} /> : null}
      <main>
        <table>
          <tbody>
            {nodes?.map((node) => (
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
