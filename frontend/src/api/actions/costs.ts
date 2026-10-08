// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the actual costs (`setActualCostTrackedScope`): the browser asks the
 * server of Next, which calls the API (§4.3.1), and gets back the outcome the one decoder makes of
 * its answer (`src/api/problem.ts`).
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Settled, settled } from "@/api/problem";
import { serverClient } from "@/api/server";

/** What the exclusion of a line from the tracked scope, or its reinstatement, takes. */
type ScopeExclusion = components["schemas"]["ScopeExclusion"];

/**
 * Exclude a line of actual cost from the tracked scope, with the reason the user gave, or
 * reinstate it (WF-CRE-0030, WF-CRE-0040): once the API has done it, the page is rendered again,
 * and reads anew the line and the three totals the server keeps — the totals follow at once, and
 * the front computes none of them.
 */
export async function setCostLineScope(
  projectId: string,
  costLineId: string,
  exclusion: ScopeExclusion,
): Promise<Settled> {
  const outcome = await decode(() =>
    serverClient().PUT("/projects/{project_id}/actual-costs/{cost_line_id}/tracked-scope", {
      params: { path: { project_id: projectId, cost_line_id: costLineId } },
      body: exclusion,
    }),
  );
  if (outcome.kind === "done") {
    refresh();
  }
  return settled(outcome);
}
