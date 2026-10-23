// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the risks of a project — one declared (`createRisk`) or modified
 * (`updateRisk`, from the version read): the browser asks the server of Next, which calls the API
 * (§4.3.1), and gets back the outcome the one decoder makes of its answer (`src/api/problem.ts`). A
 * write answered reads the page anew, which lists what the server now retains.
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome } from "@/api/problem";
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
