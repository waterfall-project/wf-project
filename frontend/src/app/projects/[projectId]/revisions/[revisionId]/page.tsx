// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of a revision, last step of the witness path (US-0080): the nodes of its main
 * structure, one row each. Scaffolding without text of its own: EP-02 replaces it with
 * the dense grid and keeps the path.
 */
import { serverClient } from "@/api/server";

/** The route parameters of a revision. */
export interface RevisionParams {
  readonly projectId: string;
  readonly revisionId: string;
}

/** Render the nodes of the main structure of a revision. */
export default async function RevisionPage({ params }: { params: Promise<RevisionParams> }) {
  const { projectId, revisionId } = await params;
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
  return (
    <main>
      <table>
        <tbody>
          {nodes?.data?.items.map((node) => (
            <tr key={node.node_id} data-kind={node.kind}>
              <td>{node.row_number}</td>
              <td>{node.task?.label ?? node.estimate_line?.label}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
