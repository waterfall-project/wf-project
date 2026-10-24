// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What a grid of the structure of a revision reads before it shows — the planning, the
 * estimate, the remaining to commit —, the same for each (EP-02, « Grille dense »): the reading
 * context of the address (WF-IHM-0020), the structure of the revision it reads — the one the address
 * names (`structure`) on the planning and the estimate, the main one by default and on every other
 * grid (US-0500) —, its version and its commands, and its nodes as the address asks them — the sort, the search, the filtered sub-project, the progress of the tasks
 * the screen narrows to, what a view that is no grid has the server select (`narrowed`), the lot
 * or the post a grid that filters by them retains (`byBreakdown`), all named as the contract
 * names them —, the sort the account keeps for the grid when the address asks none. A grid asks
 * the server what to render (`kinds`): the planning, the tasks alone; and, of each node, the
 * fields it reads alone (`fields`). A grid filtered by a lot or a post reads the work breakdown
 * whole besides, which offers them (`getWorkBreakdown`): the screen does without it, and offers
 * no filter, when the API refuses it — unless the screen needs it otherwise
 * (`needsBreakdown`). A project or a revision the API does not find is not found, as at the
 * other screens of a project; so is a structure the address names that the revision does not list.
 */
import "server-only";

import { notFound } from "next/navigation";

import type { components } from "@/api/generated/schema";
import { type ExpectedRefusal, readOrFail, readOrRefused, UnexpectedAnswer } from "@/api/problem";
import { serverClient } from "@/api/server";
import { type ProjectReading, readProjectContext } from "@/components/context/reading";
import {
  listedStructure,
  STRUCTURE_PARAMETER,
  type StructureChoices,
  type StructureKind,
} from "@/components/context/structure";
import {
  type BreakdownChoices,
  type BreakdownFilter,
  breakdownQuery,
  readBreakdownFilter,
} from "@/components/grid/breakdown-filter";
import {
  type LineField,
  type NodeField,
  type NodeFields,
  nodeFieldNames,
  type NodeFilters,
  type NodeKind,
  type NodeRow,
  type NodeRows,
  type NodeSortColumn,
  projectNodes,
  type StructurePath,
  type TaskField,
} from "@/components/grid/nodes";
import { type BreakdownItem, breakdownItems } from "@/components/grid/planning-attachment";
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

/** A command of entry a structure lists (`CostStructure.available_commands`). */
export type StructureCommand = components["schemas"]["StructureCommand"];

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
  /**
   * The states of the tasks the screen narrows the reading to — the remaining to commit, the tasks
   * started unless the address asks more (WF-RAE-0040) —; every task when none is given.
   */
  readonly progress?: NonNullable<NodeFilters["progress"]>;
  /**
   * What the server is to select of the tasks for a view that is not a grid — the summaries down
   * to a level for the task tree, the tasks of a timeline (#463) —, the view selecting nothing.
   */
  readonly narrowed?: Pick<NodeFilters, "summaries_only" | "max_level" | "timeline_id">;
  /**
   * Whether the grid is filtered by a lot or a post of the work breakdown — the planning
   * (WF-PLA-0080), the estimate (WF-DEV-0050) —, which the address names (`work_package_id`,
   * `order_item_id`) and the work breakdown read whole offers; not, when none is given.
   */
  readonly byBreakdown?: boolean;
  /**
   * Whether the screen cannot do without the work breakdown, as the reading context says — the
   * planning, where the attachment of a task is entered (WF-PLA-0170) —: a refusal of it then
   * fails the screen, as any read it needs. Never, when none is given. It is judged on the reading
   * context, `edits`, not on the structure (`commands`): it is asked while the structure is read,
   * and only on a refusal, so that it errs on the side of failing a screen the structure would
   * have read only.
   */
  readonly needsBreakdown?: (reading: ProjectReading) => boolean;
  /**
   * Whether the grid reads the structure its address names (`structure`) — the planning and the
   * estimate, on a differential or the own estimate of a risk as on the main structure (US-0500) —;
   * the main structure alone when none is given — the remaining to commit, which only the main one
   * bears (WF-RAE-0040).
   */
  readonly chooses?: boolean;
}

/**
 * What a grid of a revision shows: its context, its structure, the rows of the answer as the
 * grid reads them and the totals of the answer, its settings. The answer whole stays here.
 */
export interface GridScreen<Row> {
  readonly reading: ProjectReading;
  /** The label of the structure read. */
  readonly label: string;
  /** What the structure read is: the main one, a differential, the own estimate of a risk. */
  readonly kind: StructureKind;
  /**
   * The structure read, which a computed cell names to ask what its value depends on, and which the
   * grid is mounted for: the grid of another structure starts anew (#819.3).
   */
  readonly structure: StructurePath;
  /** The version of the structure read, which every write of the grid goes on from (#201, #819.7). */
  readonly structureVersion: number;
  /**
   * The structure read and those of the revision, which the banner names and offers; none for a
   * grid that reads the main structure alone (`GridReading.chooses`).
   */
  readonly structures: StructureChoices | undefined;
  /**
   * The commands of entry the structure read lists available to the caller: what the grid offers —
   * the entry of its cells, the gestures of the structure, the paste —, whatever the phase of the
   * project, which the front does not deduce (WF-IHM-0090). A grid whose command is not in it is
   * read only.
   */
  readonly commands: ReadonlySet<StructureCommand>;
  readonly nodes: NodeRows<Row>;
  /**
   * The level of the deepest summary of the structure, whatever the reading retains
   * (`meta.summary_depth`): the depths the task tree offers (#494).
   */
  readonly summaryDepth: number;
  /**
   * The instant of the last calculation of the dates of the structure read (`meta.scheduled_at`),
   * which the exported images of the planning name (WF-IHM-0130).
   */
  readonly scheduledAt: string;
  /**
   * What the reading asked of the nodes besides their fields and their sort — the kinds, the
   * search, the filters —, as it was sent: one that asks any has totals of its own, never those
   * of the structure a write answers, and reads them anew (`NodesWritten.totals`, #218).
   */
  readonly filters: NodeFilters;
  readonly query: GridQuery<NodeSortColumn>;
  readonly preferences: GridPreferences | undefined;
  /**
   * The lots and the posts a grid filtered by them offers, and the one the address names; none for
   * a grid that is not (`GridReading.byBreakdown`), nor when the API refuses the work breakdown.
   */
  readonly breakdown: BreakdownChoices | undefined;
  /**
   * The lot or the post the reading retains, as the address names it, whether the work breakdown
   * was read or not: the banner shows it active all the same.
   */
  readonly breakdownFilter: BreakdownFilter | undefined;
}

/** A structure of a revision, as `listCostStructures` lists it. */
type CostStructure = components["schemas"]["CostStructure"];

/**
 * The main structure of a revision, among those it lists. A revision without one, which the
 * contract rules out, is an unexpected answer, not an empty screen.
 */
export function mainStructure(structures: readonly CostStructure[]): CostStructure {
  const main = structures.find((structure) => structure.kind === "main");
  if (main === undefined) {
    throw new UnexpectedAnswer("listCostStructures", 200);
  }
  return main;
}

/**
 * The structure of the revision a grid reads, among those it lists: the one the address names, for
 * a grid that reads it (`chooses`), the main one when it names none — and for any other grid. A
 * structure the address names that the revision does not list is not found. A revision without a
 * main structure, which the contract rules out, is an unexpected answer, not an empty grid.
 */
function readStructure(
  structures: readonly CostStructure[],
  { address }: GridAddress,
  chooses: boolean,
): CostStructure {
  const main = mainStructure(structures);
  const named = chooses ? address.get(STRUCTURE_PARAMETER) : null;
  if (named === null || named === "") {
    return main;
  }
  return structures.find((structure) => structure.structure_id === named) ?? notFound();
}

/**
 * The structure of a revision a grid reads (`readStructure`), and its nodes as the address asks
 * them: sorted, searched, restricted to the filtered sub-project and to the lot or the post
 * `breakdown` names, of the kinds the grid renders, the fields it reads alone — asked of the server
 * (`fields`), and projected (`projectNodes`), the server being free to render more than asked, as
 * the fake back does. A read the API refuses, or cannot answer, is thrown for the pages of the
 * shell to say (`readOrFail`): a grid left empty would say the revision has nothing. The
 * structures are read at once; what is asked of the nodes waits for the session, whose
 * preferences may sort them.
 */
async function readStructureNodes<N extends NodeField, T extends TaskField, L extends LineField>(
  at: GridAddress,
  { kinds, fields, progress, narrowed, chooses = false }: GridReading<N, T, L>,
  breakdown: BreakdownFilter | undefined,
  asked: Promise<GridQuery<NodeSortColumn>>,
) {
  const { revision, context } = at;
  const client = serverClient();
  const path = { project_id: revision.projectId, revision_id: revision.revisionId };
  const structures = await readOrFail("listCostStructures", () =>
    client.GET("/projects/{project_id}/revisions/{revision_id}/structures", {
      params: { path },
    }),
  );
  const read = readStructure(structures, at, chooses);
  const { sort, search } = await asked;
  const subproject = context.parameters.get("subproject_id");
  const structure = { ...path, structure_id: read.structure_id };
  const filters: NodeFilters = {
    ...(kinds === undefined ? {} : { kinds: [...kinds] }),
    ...(search === undefined ? {} : { search }),
    ...(subproject === null ? {} : { subproject_id: subproject }),
    ...(progress === undefined ? {} : { progress }),
    ...narrowed,
    ...breakdownQuery(breakdown),
  };
  const answer = await readOrFail("listNodes", () =>
    client.GET("/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/nodes", {
      params: {
        path: structure,
        query: {
          fields: nodeFieldNames(fields),
          ...(sort === undefined ? {} : { sort_by: sort.column, sort_order: sort.order }),
          ...filters,
        },
      },
    }),
  );
  return {
    label: read.label,
    kind: read.kind,
    structure,
    structureVersion: read.lock_version,
    structures: chooses
      ? { read: listedStructure(read), listed: structures.map(listedStructure) }
      : undefined,
    commands: new Set(
      read.available_commands.filter((offer) => offer.is_available).map(({ command }) => command),
    ),
    nodes: projectNodes(answer, fields),
    summaryDepth: answer.meta.summary_depth,
    scheduledAt: answer.meta.scheduled_at,
    filters,
  };
}

/**
 * The refusals of the work breakdown a grid does without: the project not found to it, a reading
 * refused, the service unavailable.
 */
const BREAKDOWN_REFUSALS: readonly ExpectedRefusal[] = [
  { status: 404 },
  { status: 422 },
  { status: 503 },
];

/**
 * The lots and the posts of the work breakdown of the project read whole — a reading filtered
 * omits some —; none when the API refuses it (`BREAKDOWN_REFUSALS`) and the screen does without
 * it (`needed`), which then offers no filter. A refusal the screen cannot do without, or any
 * other answer, follows the rule of `readOrFail`.
 */
async function readBreakdownItems(
  { revision }: GridAddress,
  needed: () => Promise<boolean>,
): Promise<readonly BreakdownItem[] | undefined> {
  // The API is called once: the answer is replayed below, by the thunks the reads take.
  const answer = await serverClient().GET("/projects/{project_id}/work-breakdown", {
    params: { path: { project_id: revision.projectId } },
  });
  const read = await readOrRefused("getWorkBreakdown", BREAKDOWN_REFUSALS, () =>
    Promise.resolve(answer),
  );
  if (read.kind === "read") {
    return breakdownItems(read.data);
  }
  return (await needed())
    ? breakdownItems(await readOrFail("getWorkBreakdown", () => Promise.resolve(answer)))
    : undefined;
}

/**
 * Read what a grid of a revision shows. The settings the account keeps for the grid — `null`
 * once set back to its defaults, as none —, whose sort serves when the address says nothing of
 * the sort; the session, the structures, the reading context and the work breakdown are read
 * together, and only the nodes wait for the session.
 */
export async function readGridScreen<N extends NodeField, T extends TaskField, L extends LineField>(
  at: GridAddress,
  grid: GridReading<N, T, L>,
): Promise<GridScreen<NodeRow<N, T, L>>> {
  const settings = requestSession().then(
    (session) => session?.display_preferences?.grids?.[grid.key] ?? undefined,
  );
  const asked = settings.then((kept) => readGridQuery(at.address, grid.sortable, kept?.sort));
  const breakdownFilter = grid.byBreakdown === true ? readBreakdownFilter(at.address) : undefined;
  // The nodes are read for the filtered sub-project alone (`listNodes`): no date (#302).
  const context = readProjectContext(at.pathname, at.context, ["subproject_id"]);
  // Asked on a refusal alone: a reading context that fails is said by the reading itself.
  const needed = () =>
    context.then((read) => read !== "not_found" && grid.needsBreakdown?.(read) === true);
  const [structure, reading, preferences, query, items] = await Promise.all([
    readStructureNodes(at, grid, breakdownFilter, asked),
    context,
    settings,
    asked,
    grid.byBreakdown === true ? readBreakdownItems(at, needed) : undefined,
  ]);
  if (reading === "not_found") {
    notFound();
  }
  const breakdown = items === undefined ? undefined : { items, filter: breakdownFilter };
  return { reading, ...structure, query, preferences, breakdown, breakdownFilter };
}
