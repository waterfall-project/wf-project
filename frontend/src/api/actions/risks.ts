// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the risks of a project — one declared (`createRisk`) or modified
 * (`updateRisk`, from the version read), reviewed (`reviewRisk`), deleted (`deleteRisk`) or declared
 * occurred (`declareRiskOccurrence`): the browser asks the server of Next, which calls the API
 * (§4.3.1), and gets back the outcome the one decoder makes of its answer (`src/api/problem.ts`). A
 * write answered reads the page anew, which lists what the server now retains — but for the deletion,
 * which the screen leaves for the address without the risk, and the occurrence, handed to the worker,
 * which the tracker of the shell follows.
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

/**
 * Declare a risk (WF-RIS-0010), or modify one from the version read: the API answers it as it now
 * is — a declaration with the structure of its own estimate, which the screen leads to —, or refuses
 * it: the commands that lack (409, `active_provision_category`, `at_least_one_task`), a field (422).
 */
export async function writeRisk(
  projectId: string,
  write:
    | { readonly id: undefined; readonly body: Schemas["RiskWrite"] }
    | { readonly id: string; readonly body: Schemas["RiskUpdate"] },
): Promise<Outcome<Schemas["Risk"]>> {
  const client = serverClient();
  const project = { project_id: projectId };
  const outcome = await decode(() =>
    write.id === undefined
      ? client.POST("/projects/{project_id}/risks", {
          params: { path: project },
          body: write.body,
        })
      : client.PATCH("/projects/{project_id}/risks/{risk_id}", {
          params: { path: { ...project, risk_id: write.id } },
          body: write.body,
        }),
  );
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/**
 * Review a risk, from the version read (WF-RIS-0010, WF-RIS-0020): the probability and the state
 * retained, the category asked of a risk dismissed that returns to identified when the one it
 * designated is no longer active. The API answers the risk as it now is, and dates the review; it
 * refuses a risk occurred (409, `risk_not_occurred`), a return with no category active (409,
 * `active_provision_category`), a probability out of its bounds (422).
 */
export async function reviewRisk(
  projectId: string,
  riskId: string,
  body: Schemas["RiskReviewWrite"],
): Promise<Outcome<Schemas["Risk"]>> {
  const outcome = await decode(() =>
    serverClient().POST("/projects/{project_id}/risks/{risk_id}/reviews", {
      params: { path: { project_id: projectId, risk_id: riskId } },
      body,
    }),
  );
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/**
 * Delete a risk with its own estimate and its line of provision (WF-RIS-0020): refused (409) when a
 * marked revision cites it (`risk_not_cited`) or it occurred (`risk_not_occurred`). The page is not
 * read anew here: it names the risk, which is gone, and the screen leaves it for the address without.
 */
export async function deleteRisk(projectId: string, riskId: string): Promise<Settled> {
  return settled(
    await decode(() =>
      serverClient().DELETE("/projects/{project_id}/risks/{risk_id}", {
        params: { path: { project_id: projectId, risk_id: riskId } },
      }),
    ),
  );
}

/**
 * Declare a risk occurred (WF-RIS-0060): the API hands the merge of its own estimate into the main
 * structure to the worker and answers at once with the reference of the background task
 * (WF-ARC-0090), which the tracker of the shell follows. Final.
 */
export async function declareRiskOccurrence(
  projectId: string,
  riskId: string,
): Promise<Outcome<BackgroundTask>> {
  return decodeTask(() =>
    serverClient().POST("/projects/{project_id}/risks/{risk_id}/occurrence", {
      params: { path: { project_id: projectId, risk_id: riskId } },
      body: { confirmed: true },
    }),
  );
}
