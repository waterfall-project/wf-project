// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the reference data — a cell of the grid of the hourly rates entered
 * (`setHourlyRate`), an object deactivated reactivated (`reactivate`) —: the screen asks the server
 * of Next, which calls the API (§4.3.1), and gets back the outcome the one decoder makes of its
 * answer (`src/api/problem.ts`).
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome, type Settled, settled } from "@/api/problem";
import { serverClient } from "@/api/server";

/** The hourly rate of a category of labour for a year, as the server answers it. */
type HourlyRate = components["schemas"]["HourlyRate"];

/**
 * Write the hourly rate of a category for a year (WF-REF-0050): the first one of the year without
 * a version, a correction with the version of the rate read — a correction affects no marked
 * revision (WF-REF-0130). The API answers the rate as it now is, or refuses it.
 */
export async function setHourlyRate(
  costCategoryId: string,
  year: number,
  rate: components["schemas"]["HourlyRateWrite"],
): Promise<Outcome<HourlyRate>> {
  return decode(() =>
    serverClient().PUT("/reference/cost-categories/{cost_category_id}/hourly-rates/{year}", {
      params: { path: { cost_category_id: costCategoryId, year } },
      body: rate,
    }),
  );
}

/**
 * An object of the reference data that may be deactivated and reactivated (WF-REF-0150), by its
 * kind, its identifier and the version read.
 */
export interface ActivationTarget {
  readonly kind: "org_node" | "resource_role" | "calendar" | "cost_type" | "cost_category";
  readonly id: string;
  readonly lockVersion: number;
}

/** The activation each kind of object takes: active again, from the version read. */
function activation(target: ActivationTarget) {
  return { is_active: true, lock_version: target.lockVersion };
}

/** Ask the API to reactivate an object, by the operation of its kind. */
function reactivation(target: ActivationTarget) {
  const client = serverClient();
  const body = activation(target);
  switch (target.kind) {
    case "org_node":
      return client.PUT("/reference/org-nodes/{org_node_id}/activation", {
        params: { path: { org_node_id: target.id } },
        body,
      });
    case "resource_role":
      return client.PUT("/reference/resource-roles/{resource_role_id}/activation", {
        params: { path: { resource_role_id: target.id } },
        body,
      });
    case "calendar":
      return client.PUT("/reference/calendars/{calendar_id}/activation", {
        params: { path: { calendar_id: target.id } },
        body,
      });
    case "cost_type":
      return client.PUT("/reference/cost-types/{cost_type_id}/activation", {
        params: { path: { cost_type_id: target.id } },
        body,
      });
    case "cost_category":
      return client.PUT("/reference/cost-categories/{cost_category_id}/activation", {
        params: { path: { cost_category_id: target.id } },
        body,
      });
  }
}

/**
 * Reactivate an object of the reference data a list shows deactivated (WF-REF-0150), from the
 * version read: once the API has done it, the page is rendered again, and reads the list anew —
 * the object active, and what the server reactivated with it. Nothing is deleted nor deactivated
 * here.
 */
export async function reactivate(target: ActivationTarget): Promise<Settled> {
  const outcome = await decode<unknown>(() => reactivation(target));
  if (outcome.kind === "done") {
    refresh();
  }
  return settled(outcome);
}
