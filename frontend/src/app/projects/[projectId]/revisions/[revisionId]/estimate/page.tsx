// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The grid of the estimate of a revision (WF-DEV-0050, US-0110), at the route of its function
 * (`functions.json`): the banner of its reading context (WF-IHM-0020), and the grid on the main
 * structure of the revision. The server reads the structure as the address asks — the sort, the
 * search, the filtered sub-project, all named as the contract names them —, the sort the account
 * keeps for the grid when the address asks none; the grid shows the rows in the order of the
 * answer, with the totals of the answer: a header clicked or a search entered changes the
 * address, and this page reads anew. A project or a revision the API does not find is not
 * found, as at the other screens of a project.
 */
import { notFound } from "next/navigation";
import { useTranslations } from "next-intl";

import { readOrFail, UnexpectedAnswer } from "@/api/problem";
import { serverClient } from "@/api/server";
import { ContextBanner } from "@/components/context/context-banner";
import { readProjectContext } from "@/components/context/reading";
import {
  ESTIMATE_GRID,
  ESTIMATE_SORT_COLUMNS,
  type NodeList,
  type NodeSortColumn,
} from "@/components/grid/estimate";
import { EstimateGrid } from "@/components/grid/estimate-grid";
import { type GridQuery, readGridQuery } from "@/components/grid/query";
import { FUNCTION_DENSITY, FUNCTION_ICONS } from "@/components/shell/function-display";
import { PageHeader, Screen } from "@/components/shell/page-header";
import {
  type PageSearchParams,
  pageSearch,
  type ProjectContext,
  readContext,
} from "@/navigation/context";
import { requestSession } from "@/session/request";

import type { RevisionParams } from "../page";

/**
 * The main structure of a revision, and its nodes as the address asks them: sorted, searched,
 * restricted to the filtered sub-project. A read the API refuses, or cannot answer, is thrown
 * for the pages of the shell to say (`readOrFail`): a grid left empty would say the revision
 * has nothing. So is a revision without a main structure, which the contract rules out: an
 * answer of the API that breaks it is unexpected, not an empty grid. The structures are read
 * at once; what is asked of the nodes waits for the session, whose preferences may sort them.
 */
async function mainStructure(
  { projectId, revisionId }: RevisionParams,
  context: ProjectContext,
  asked: Promise<GridQuery<NodeSortColumn>>,
) {
  const client = serverClient();
  const revision = { project_id: projectId, revision_id: revisionId };
  const structures = await readOrFail("listCostStructures", () =>
    client.GET("/projects/{project_id}/revisions/{revision_id}/structures", {
      params: { path: revision },
    }),
  );
  const main = structures.find((structure) => structure.kind === "main");
  if (main === undefined) {
    throw new UnexpectedAnswer("listCostStructures", 200);
  }
  const { sort, search } = await asked;
  const subproject = context.parameters.get("subproject_id");
  const nodes = await readOrFail("listNodes", () =>
    client.GET("/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes", {
      params: {
        path: { ...revision, structure_id: main.structure_id },
        query: {
          ...(sort === undefined ? {} : { sort_by: sort.column, sort_order: sort.order }),
          ...(search === undefined ? {} : { search }),
          ...(subproject === null ? {} : { subproject_id: subproject }),
        },
      },
    }),
  );
  return { label: main.label, nodes };
}

/** The title of the grid, and what it holds: the structure, its tasks and lines retained. */
function EstimateHeader({ label, nodes }: { readonly label: string; readonly nodes: NodeList }) {
  const t = useTranslations();
  return (
    <PageHeader
      title={t("functions.estimate")}
      icon={FUNCTION_ICONS.estimate}
      density={FUNCTION_DENSITY.estimate}
      subtitle={t("estimateGrid.summary", {
        structure: label,
        tasks: nodes.totals.task_count,
        lines: nodes.totals.estimate_line_count,
      })}
    />
  );
}

/** Render the grid of the estimate on the main structure of a revision. */
export default async function EstimatePage({
  params,
  searchParams,
}: {
  params: Promise<RevisionParams>;
  searchParams: Promise<PageSearchParams>;
}) {
  const [revision, search] = await Promise.all([params, searchParams]);
  const pathname = `/projects/${revision.projectId}/revisions/${revision.revisionId}/estimate`;
  const address = pageSearch(search);
  // An address that names no project or no revision is not found before the API is asked.
  const context = readContext(pathname, address);
  if (context === undefined) {
    notFound();
  }
  // The settings the account keeps for the grid — `null` once set back to its defaults, as
  // none —, whose sort serves when the address says nothing of the sort. The session, the
  // structures and the reading context are read together; only the nodes wait for the session.
  const settings = requestSession().then(
    (session) => session?.user.display_preferences?.grids?.[ESTIMATE_GRID.key] ?? undefined,
  );
  const asked = settings.then((kept) => readGridQuery(address, ESTIMATE_SORT_COLUMNS, kept?.sort));
  const [structure, read, preferences, query] = await Promise.all([
    mainStructure(revision, context, asked),
    readProjectContext(pathname, context),
    settings,
    asked,
  ]);
  if (read === "not_found") {
    notFound();
  }
  return (
    <>
      <ContextBanner reading={read} />
      <Screen density={FUNCTION_DENSITY.estimate}>
        <EstimateHeader label={structure.label} nodes={structure.nodes} />
        <EstimateGrid nodes={structure.nodes} query={query} preferences={preferences} />
      </Screen>
    </>
  );
}
