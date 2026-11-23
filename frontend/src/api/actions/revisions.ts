// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the revisions of a project — marked (`markRevision`), opened
 * (`createRevision`), abandoned (`abandonRevision`), designated as the reference
 * (`designateReferenceRevision`), their rates proposed (`readRateUpdateProposal`) and updated
 * (`applyRateUpdate`), an amendment prepared
 * (`prepareAmendment`), its merge read (`readMergeReport`) and confirmed (`mergeAmendment`), its
 * update from the main structure read (`readRebaseReport`) and confirmed (`rebaseStructure`) —
 * the own estimate of a risk is updated and recomposed (`recomposeStructure`) likewise —, and
 * abandoned (`abandonAmendment`): the browser asks the
 * server of Next, which calls the API (§4.3.1), and gets back the outcome the one decoder makes
 * of its answer (`src/api/problem.ts`). A write answered reads the page anew: the state of the
 * project, its banner, the commands of its revisions are the server's again.
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import {
  type BackgroundTask,
  decode,
  decodeTask,
  type Outcome,
  type Settled,
  settled,
} from "@/api/problem";
import { serverClient } from "@/api/server";

type Schemas = components["schemas"];

/** What marking a revision takes: its version name, and the version of the revision read. */
type RevisionMark = Schemas["RevisionMark"];

/** Read the page anew once the API has answered a write. */
function readAnew<T>(outcome: Outcome<T>): Outcome<T> {
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/**
 * Mark a revision under a version name (WF-REV-0020): the API hands the marking to the worker
 * and answers at once with the reference of the background task (WF-ARC-0090), which the
 * tracker of the shell follows. A version name already taken, a revision already marked or
 * read in an older version are refusals of the API, told as such.
 */
export async function markRevision(
  projectId: string,
  revisionId: string,
  mark: RevisionMark,
): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() =>
    serverClient().POST("/projects/{project_id}/revisions/{revision_id}/mark", {
      params: { path: { project_id: projectId, revision_id: revisionId } },
      body: mark,
    }),
  );
}

/**
 * Open the current revision of a project, copied from its last marked revision (WF-REV-0010): the
 * API answers the revision created, or refuses a second one while one is current (409).
 */
export async function createRevision(
  projectId: string,
  create: Schemas["RevisionCreate"],
): Promise<Outcome<Schemas["Revision"]>> {
  return readAnew(
    await decode(() =>
      serverClient().POST("/projects/{project_id}/revisions", {
        params: { path: { project_id: projectId } },
        body: create,
      }),
    ),
  );
}

/**
 * Abandon the current revision (WF-REV-0010): the project returns to its last marked revision. The
 * page is not read anew here: its address names a revision that is no more, and the screen leaves it.
 */
export async function abandonRevision(
  projectId: string,
  revisionId: string,
  lockVersion: number,
): Promise<Settled> {
  return settled(
    await decode(() =>
      serverClient().DELETE("/projects/{project_id}/revisions/{revision_id}", {
        params: {
          path: { project_id: projectId, revision_id: revisionId },
          query: { lock_version: lockVersion },
        },
      }),
    ),
  );
}

/**
 * Designate a marked revision as the reference of the project (WF-REV-0040): the API answers the
 * project, in progress if it bears its code (WF-CYC-0030), or refuses, naming the condition that
 * is lacking (409), or the project moved since the counter read (412, WF-IHM-0110).
 */
export async function designateReferenceRevision(
  projectId: string,
  revisionId: string,
  projectLockVersion: number,
): Promise<Outcome<Schemas["Project"]>> {
  return readAnew(
    await decode(() =>
      serverClient().PUT("/projects/{project_id}/reference-revision", {
        params: { path: { project_id: projectId } },
        body: { revision_id: revisionId, confirmed: true, lock_version: projectLockVersion },
      }),
    ),
  );
}

/**
 * Read the update of the rates the API proposes to the current revision, category by category
 * (WF-REV-0060): a read, which writes nothing, made when the dialog of the update opens and not
 * when the screen renders; abandoning at this step is not applying.
 */
export async function readRateUpdateProposal(
  projectId: string,
  revisionId: string,
): Promise<Outcome<Schemas["RateUpdateProposal"]>> {
  return decode(() =>
    serverClient().GET("/projects/{project_id}/revisions/{revision_id}/rate-update", {
      params: { path: { project_id: projectId, revision_id: revisionId } },
    }),
  );
}

/**
 * Apply the update of the rates the API proposes to the current revision, for the categories
 * retained, from the version read (WF-REV-0060): the API answers the revision, or refuses a revision
 * marked (409) or read in an older version (412).
 */
export async function applyRateUpdate(
  projectId: string,
  revisionId: string,
  update: { readonly categoryIds: readonly string[]; readonly lockVersion: number },
): Promise<Outcome<Schemas["Revision"]>> {
  return readAnew(
    await decode(() =>
      serverClient().POST("/projects/{project_id}/revisions/{revision_id}/rate-update", {
        params: { path: { project_id: projectId, revision_id: revisionId } },
        body: { cost_category_ids: [...update.categoryIds], lock_version: update.lockVersion },
      }),
    ),
  );
}

/**
 * Prepare an amendment (WF-REV-0100): a differential of the main structure of the current revision,
 * under the label the user gave. The API answers the structure created, which the screen opens in the
 * grid of the planning, or refuses a revision that is no more current (409).
 */
export async function prepareAmendment(
  projectId: string,
  revisionId: string,
  label: string,
): Promise<Outcome<Schemas["CostStructure"]>> {
  return readAnew(
    await decode(() =>
      serverClient().POST("/projects/{project_id}/revisions/{revision_id}/structures", {
        params: { path: { project_id: projectId, revision_id: revisionId } },
        body: { kind: "amendment", label },
      }),
    ),
  );
}

/**
 * Read what merging an amendment would do (WF-REV-0050): the report that is shown before anything is
 * applied, with the two counters the confirmation carries. A read, which writes nothing: abandoning at
 * this step is not confirming.
 */
export async function readMergeReport(
  projectId: string,
  revisionId: string,
  structureId: string,
): Promise<Outcome<Schemas["StructureMergeReport"]>> {
  return decode(() =>
    serverClient().GET(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/merge",
      {
        params: {
          path: { project_id: projectId, revision_id: revisionId, structure_id: structureId },
        },
      },
    ),
  );
}

/** What confirming the merge of an amendment takes: its version name, and the counters the report read. */
export interface AmendmentMerge {
  readonly versionName: string;
  /** The description joined to the revision marked, as at the marking (WF-REV-0020); none when empty. */
  readonly description?: string | undefined;
  readonly mainStructureLockVersion: number;
  readonly amendmentLockVersion: number;
}

/**
 * Merge an amendment into the main structure, marking the revision under the version name given
 * (WF-REV-0050): the API hands the merge to the worker and answers at once with the reference of the
 * background task (WF-ARC-0090), which the tracker of the shell follows. A report that went stale — a
 * counter moved since it was read — is refused (412), and nothing is merged.
 */
export async function mergeAmendment(
  projectId: string,
  revisionId: string,
  structureId: string,
  merge: AmendmentMerge,
): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() =>
    serverClient().POST(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/merge",
      {
        params: {
          path: { project_id: projectId, revision_id: revisionId, structure_id: structureId },
        },
        body: {
          confirmed: true,
          version_name: merge.versionName,
          ...(merge.description === undefined || merge.description === ""
            ? {}
            : { description: merge.description }),
          main_structure_lock_version: merge.mainStructureLockVersion,
          amendment_lock_version: merge.amendmentLockVersion,
        },
      },
    ),
  );
}

/**
 * Abandon an amendment (WF-REV-0100): the differential, and the base that nobody reads, are deleted,
 * from the counter the screen read. The page is not read anew here: its address names a structure that
 * is no more, and the screen leaves it for the main structure. A differential merged, a revision
 * marked or a project terminal are refused (409), a counter that moved since it was read, 412.
 */
export async function abandonAmendment(
  projectId: string,
  revisionId: string,
  structureId: string,
  lockVersion: number,
): Promise<Settled> {
  return settled(
    await decode(() =>
      serverClient().DELETE(
        "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}",
        {
          params: {
            path: { project_id: projectId, revision_id: revisionId, structure_id: structureId },
            query: { lock_version: lockVersion },
          },
        },
      ),
    ),
  );
}

/**
 * Read what updating an amendment, or the own estimate of a risk, from the main structure would do
 * (#4034, US-3140): the report that is shown
 * before anything is written — what the main structure received since its base, what the structure
 * keeps, what refuses —, with the two counters the confirmation carries, and, for an own estimate, the
 * severity and the provision the update would record. A read, which writes nothing.
 */
export async function readRebaseReport(
  projectId: string,
  revisionId: string,
  structureId: string,
): Promise<Outcome<Schemas["StructureRebaseReport"]>> {
  return decode(() =>
    serverClient().GET(
      "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/rebase",
      {
        params: {
          path: { project_id: projectId, revision_id: revisionId, structure_id: structureId },
        },
      },
    ),
  );
}

/** What confirming the update of a structure takes: the counters the report read. */
export interface StructureRebase {
  readonly mainStructureLockVersion: number;
  readonly structureLockVersion: number;
}

/**
 * Update an amendment, or the own estimate of a risk, from the main structure (#4034): the API writes
 * into it what the report presented and makes the main structure its new base, answering the
 * structure, up to date. A report gone stale — a counter moved since it was read — is refused (412)
 * and nothing is written, as a reason of the report (422) or a structure already up to date (409). The
 * page is read anew: the grid of the structure is the server's again.
 */
export async function rebaseStructure(
  projectId: string,
  revisionId: string,
  structureId: string,
  rebase: StructureRebase,
): Promise<Outcome<Schemas["CostStructure"]>> {
  return readAnew(
    await decode(() =>
      serverClient().POST(
        "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/rebase",
        {
          params: {
            path: { project_id: projectId, revision_id: revisionId, structure_id: structureId },
          },
          body: {
            confirmed: true,
            main_structure_lock_version: rebase.mainStructureLockVersion,
            structure_lock_version: rebase.structureLockVersion,
          },
        },
      ),
    ),
  );
}

/**
 * Recompose the own estimate of a risk that a marking pruned (US-3140, `recomposeCostStructure`): the
 * API makes it whole again, from the main structure of the marked revision it names, what it
 * designates unchanged, and answers the structure — up to date, or out of date when the main structure
 * has changed since. It takes no body and asks no confirmation. The page is read anew: the grid of the
 * own estimate is the server's again.
 */
export async function recomposeStructure(
  projectId: string,
  revisionId: string,
  structureId: string,
): Promise<Outcome<Schemas["CostStructure"]>> {
  return readAnew(
    await decode(() =>
      serverClient().POST(
        "/projects/{project_id}/revisions/{revision_id}/structures/{structure_id}/recompose",
        {
          params: {
            path: { project_id: projectId, revision_id: revisionId, structure_id: structureId },
          },
        },
      ),
    ),
  );
}
