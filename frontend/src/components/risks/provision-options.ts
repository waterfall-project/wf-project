// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the form of a risk offers to choose for its provision (WF-RIS-0010, EP-14/L42p, #786): the
 * categories of cost that are of the type provision for risks — active, under a nature active —,
 * read from the reference data (`listCostCategories`, `cost_type_kind`); the sub-projects of the
 * project (`listSubprojects`); and the tasks of the main structure of the revision, which may bear
 * the provision line (`listNodes`). Read on the server when the screen offers a form, and handed to
 * it as data: an identifier and a label for each choice, in the order the API gives them.
 *
 * A session that may not read the reference data (403) is offered no category: the form does not ask
 * for one, and the server, which judges the declaration, says what the risk lacks.
 */
import "server-only";

import { readEveryPageUnlessRefused } from "@/api/every-page";
import { readOrFail, UnexpectedAnswer } from "@/api/problem";
import { serverClient } from "@/api/server";
import { askSubprojects } from "@/components/context/reading";

import type { ProvisionOptions } from "./provision-choices";

/** The active categories of cost of the type provision for risks; none when the session may not read them. */
async function readCategories(): Promise<ProvisionOptions["categories"]> {
  const read = await readEveryPageUnlessRefused("listCostCategories", [{ status: 403 }], (page) =>
    serverClient().GET("/reference/cost-categories", { params: { query: page } }),
  );
  return (read ?? [])
    .filter(
      ({ cost_type_kind: kind, cost_type_is_active: natureActive, is_active: active }) =>
        kind === "provision" && natureActive && active,
    )
    .map(({ cost_category_id: id, label }) => ({ id, label }));
}

/** The tasks of the main structure of a revision, in the order of the plan. */
async function readTasks(
  projectId: string,
  revisionId: string,
): Promise<ProvisionOptions["tasks"]> {
  const client = serverClient();
  const path = { project_id: projectId, revision_id: revisionId };
  const structures = await readOrFail("listCostStructures", () =>
    client.GET("/projects/{project_id}/revisions/{revision_id}/structures", { params: { path } }),
  );
  const main = structures.find(({ kind }) => kind === "main");
  if (main === undefined) {
    throw new UnexpectedAnswer("listCostStructures", 200);
  }
  const nodes = await readOrFail("listNodes", () =>
    client.GET("/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes", {
      params: {
        path: { ...path, structure_id: main.structure_id },
        query: { kinds: ["task"], fields: ["task.label"] },
      },
    }),
  );
  // The fake back ignores the filter of the kinds: the tasks are kept once more.
  return nodes.items.flatMap(({ node_id: id, kind, task }) =>
    kind === "task" && task !== undefined && task !== null ? [{ id, label: task.label }] : [],
  );
}

/** Read what the form of a risk of a revision chooses its provision among. */
export async function readProvisionOptions(
  projectId: string,
  revisionId: string,
): Promise<ProvisionOptions> {
  const [categories, subprojects, tasks] = await Promise.all([
    readCategories(),
    readOrFail("listSubprojects", () => askSubprojects(projectId)),
    readTasks(projectId, revisionId),
  ]);
  return {
    categories,
    subprojects: subprojects.map(({ subproject_id: id, label }) => ({ id, label })),
    tasks,
  };
}
