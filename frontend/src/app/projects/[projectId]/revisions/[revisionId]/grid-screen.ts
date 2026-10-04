// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a grid of the structure of a revision reads before it shows — the planning, the
 * estimate —, the same for both (EP-02, « Grille dense »): the reading context of the address
 * (WF-IHM-0020), the main structure of the revision, and its nodes as the address asks them —
 * the sort, the search, the filtered sub-project, all named as the contract names them —, the
 * sort the account keeps for the grid when the address asks none. A grid asks the server what
 * to render (`kinds`): the planning, the tasks alone; and, of each node, the fields it reads
 * alone (`fields`). A project or a revision the API does not find is not found, as at the other
 * screens of a project.
 */
import "server-only";

import { notFound } from "next/navigation";

import { readOrFail, UnexpectedAnswer } from "@/api/problem";
import { serverClient } from "@/api/server";
import { type ProjectReading, readProjectContext } from "@/components/context/reading";
import {
  type LineField,
  type NodeField,
  type NodeFields,
  nodeFieldNames,
  type NodeKind,
  type NodeRow,
  type NodeRows,
  type NodeSortColumn,
  projectNodes,
  type StructurePath,
  type TaskField,
} from "@/components/grid/nodes";
import { type GridQuery, readGridQuery } from "@/components/grid/query";
import type { GridPreferences } from "@/components/grid/settings";
import {
  type PageSearchParams,
  pageSearch,
  type ProjectContext,
  readContext,
  type SearchParameters,
} from "@/navigation/context";
import { requestSession } from "@/session/request";

import type { RevisionParams } from "./page";

/** The address of a screen of a revision, and the context it names. */
export interface GridAddress {
  readonly revision: RevisionParams;
  readonly pathname: string;
  readonly address: SearchParameters;
  readonly context: ProjectContext;
}

/**
 * The address of the screen of a function of a revision — `planning`, `estimate` —, and the
 * context it names: an address that names no project or no revision is not found before the
 * API is asked anything.
 */
export function gridAddress(
  revision: RevisionParams,
  search: PageSearchParams,
  segment: string,
): GridAddress {
  const pathname = `/projects/${revision.projectId}/revisions/${revision.revisionId}/${segment}`;
  const address = pageSearch(search);
  const context = readContext(pathname, address);
  if (context === undefined) {
    notFound();
  }
  return { revision, pathname, address, context };
}

/**
 * What a grid is: the key of its settings, the columns it sorts, what it renders, and the fields
 * of a node it reads — `N` of the node, `T` of its task, `L` of its line.
 */
export interface GridReading<N extends NodeField, T extends TaskField, L extends LineField> {
  readonly key: string;
  readonly sortable: readonly NodeSortColumn[];
  /** What the server is to render; every kind of node when none is given. */
  readonly kinds?: readonly NodeKind[];
  /** The fields of each node the grid reads, besides those every grid reads. */
  readonly fields: NodeFields<N, T, L>;
}

/**
 * What a grid of a revision shows: its context, its structure, the rows of the answer as the
 * grid reads them and the totals of the answer, its settings. The answer whole stays here.
 */
export interface GridScreen<Row> {
  readonly reading: ProjectReading;
  /** The label of the main structure. */
  readonly label: string;
  /** The main structure, which a computed cell names to ask what its value depends on. */
  readonly structure: StructurePath;
  /** The version of the main structure read, which a paste applied carries (#201). */
  readonly structureVersion: number;
  readonly nodes: NodeRows<Row>;
  /**
   * Whether the nodes were read under a search or a filter: the totals are then those of the
   * reading alone, never those of the structure a write answers (`NodesWritten.totals`, #218).
   */
  readonly filtered: boolean;
  readonly query: GridQuery<NodeSortColumn>;
  readonly preferences: GridPreferences | undefined;
}

/**
 * The main structure of a revision, and its nodes as the address asks them: sorted, searched,
 * restricted to the filtered sub-project, of the kinds the grid renders, the fields it reads
 * alone — asked of the server (`fields`), and projected (`projectNodes`), the server being free
 * to render more than asked, as the fake back does. A read the API refuses,
 * or cannot answer, is thrown for the pages of the shell to say (`readOrFail`): a grid left
 * empty would say the revision has nothing. So is a revision without a main structure, which
 * the contract rules out: an answer of the API that breaks it is unexpected, not an empty grid.
 * The structures are read at once; what is asked of the nodes waits for the session, whose
 * preferences may sort them.
 */
async function mainStructure<N extends NodeField, T extends TaskField, L extends LineField>(
  { revision, context }: GridAddress,
  { kinds, fields }: GridReading<N, T, L>,
  asked: Promise<GridQuery<NodeSortColumn>>,
) {
  const client = serverClient();
  const path = { project_id: revision.projectId, revision_id: revision.revisionId };
  const structures = await readOrFail("listCostStructures", () =>
    client.GET("/projects/{project_id}/revisions/{revision_id}/structures", {
      params: { path },
    }),
  );
  const main = structures.find((structure) => structure.kind === "main");
  if (main === undefined) {
    throw new UnexpectedAnswer("listCostStructures", 200);
  }
  const { sort, search } = await asked;
  const subproject = context.parameters.get("subproject_id");
  const structure = { ...path, structure_id: main.structure_id };
  const answer = await readOrFail("listNodes", () =>
    client.GET("/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes", {
      params: {
        path: structure,
        query: {
          fields: nodeFieldNames(fields),
          ...(kinds === undefined ? {} : { kinds: [...kinds] }),
          ...(sort === undefined ? {} : { sort_by: sort.column, sort_order: sort.order }),
          ...(search === undefined ? {} : { search }),
          ...(subproject === null ? {} : { subproject_id: subproject }),
        },
      },
    }),
  );
  return {
    label: main.label,
    structure,
    structureVersion: main.lock_version,
    nodes: projectNodes(answer, fields),
    filtered: search !== undefined || subproject !== null,
  };
}

/**
 * Read what a grid of a revision shows. The settings the account keeps for the grid — `null`
 * once set back to its defaults, as none —, whose sort serves when the address says nothing of
 * the sort; the session, the structures and the reading context are read together, and only
 * the nodes wait for the session.
 */
export async function readGridScreen<N extends NodeField, T extends TaskField, L extends LineField>(
  at: GridAddress,
  grid: GridReading<N, T, L>,
): Promise<GridScreen<NodeRow<N, T, L>>> {
  const settings = requestSession().then(
    (session) => session?.user.display_preferences?.grids?.[grid.key] ?? undefined,
  );
  const asked = settings.then((kept) => readGridQuery(at.address, grid.sortable, kept?.sort));
  const [structure, reading, preferences, query] = await Promise.all([
    mainStructure(at, grid, asked),
    readProjectContext(at.pathname, at.context),
    settings,
    asked,
  ]);
  if (reading === "not_found") {
    notFound();
  }
  return { reading, ...structure, query, preferences };
}
