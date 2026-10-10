// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the reference data — a cell of the grid of the hourly rates entered
 * (`setHourlyRate`); a node of the organisation, a resource role, a calendar, a nature or a category
 * of cost created, modified, deactivated or reactivated (`createReferenceObject`,
 * `updateReferenceObject`, `setActivation`); a calendar designated by default
 * (`designateDefaultCalendar`); the risk matrix, or the thresholds of the indices and the delay
 * between two reviews, written (`updateReferenceSettings`) —: the screen asks the server of Next, which calls the API (§4.3.1),
 * and gets back the outcome the one decoder makes of its answer (`src/api/problem.ts`). Nothing is
 * deleted (WF-REF-0010).
 */
"use server";

import { refresh } from "next/cache";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome } from "@/api/problem";
import { serverClient } from "@/api/server";

type Schemas = components["schemas"];

/** The hourly rate of a category of labour for a year, as the server answers it. */
type HourlyRate = Schemas["HourlyRate"];

/**
 * Write the hourly rate of a category for a year (WF-REF-0050): the first one of the year without
 * a version, a correction with the version of the rate read — a correction affects no marked
 * revision (WF-REF-0130). The API answers the rate as it now is, or refuses it. A first rate answered
 * reads the page anew: a category that bears rates is no longer attached to a nature of another type
 * (`cost_category_unrated`, #577), a command of the list of the categories its answer does not carry;
 * a first rate refused as a second one for its year (409 `ALREADY_EXISTS`, WF-REF-0050) reads it
 * anew too, for the cell to show the rate the year holds, with its version. A correction changes no
 * command, and the page is not read for it.
 */
export async function setHourlyRate(
  costCategoryId: string,
  year: number,
  rate: Schemas["HourlyRateWrite"],
): Promise<Outcome<HourlyRate>> {
  const outcome = await decode(() =>
    serverClient().PUT("/reference/cost-categories/{cost_category_id}/hourly-rates/{year}", {
      params: { path: { cost_category_id: costCategoryId, year } },
      body: rate,
    }),
  );
  if (rate.lock_version !== undefined) {
    return outcome;
  }
  // A first rate refused for a year that holds one already (409): the page read anew shows it with
  // its version, and the next entry corrects it rather than meeting the same refusal again.
  if (outcome.kind === "conflict" && outcome.problem.code === "ALREADY_EXISTS") {
    refresh();
    return outcome;
  }
  return readAnew(outcome);
}

/** An object of the reference data a screen writes, as the server answers a write of it. */
export type ReferenceObject =
  | Schemas["OrgNode"]
  | Schemas["ResourceRole"]
  | Schemas["Calendar"]
  | Schemas["CostType"]
  | Schemas["CostCategory"];

/** The kind of an object of the reference data that is deactivated and reactivated (WF-REF-0010). */
export type ReferenceKind =
  "org_node" | "resource_role" | "calendar" | "cost_type" | "cost_category";

/**
 * An object of the reference data that may be deactivated and reactivated (WF-REF-0150), by its
 * kind, its identifier and the version read.
 */
export interface ActivationTarget {
  readonly kind: ReferenceKind;
  readonly id: string;
  readonly lockVersion: number;
}

/** Ask the API to activate or deactivate an object, by the operation of its kind, from the version read. */
async function activation(
  target: ActivationTarget,
  active: boolean,
): Promise<Outcome<readonly ReferenceObject[]>> {
  const client = serverClient();
  const body = { is_active: active, lock_version: target.lockVersion };
  const one = (outcome: Outcome<ReferenceObject>): Outcome<readonly ReferenceObject[]> =>
    outcome.kind === "done" ? { kind: "done", data: [outcome.data] } : outcome;
  switch (target.kind) {
    case "org_node": {
      const outcome = await decode(() =>
        client.PUT("/reference/org-nodes/{org_node_id}/activation", {
          params: { path: { org_node_id: target.id } },
          body,
        }),
      );
      // The nodes whose state changed, the cascade applied; the roles are the other list's.
      return outcome.kind === "done" ? { kind: "done", data: outcome.data.org_nodes } : outcome;
    }
    case "resource_role":
      return one(
        await decode(() =>
          client.PUT("/reference/resource-roles/{resource_role_id}/activation", {
            params: { path: { resource_role_id: target.id } },
            body,
          }),
        ),
      );
    case "calendar":
      return one(
        await decode(() =>
          client.PUT("/reference/calendars/{calendar_id}/activation", {
            params: { path: { calendar_id: target.id } },
            body,
          }),
        ),
      );
    case "cost_type":
      return one(
        await decode(() =>
          client.PUT("/reference/cost-types/{cost_type_id}/activation", {
            params: { path: { cost_type_id: target.id } },
            body,
          }),
        ),
      );
    case "cost_category":
      return one(
        await decode(() =>
          client.PUT("/reference/cost-categories/{cost_category_id}/activation", {
            params: { path: { cost_category_id: target.id } },
            body,
          }),
        ),
      );
  }
}

/**
 * Read the page anew once an object is written: an object is what others are filtered on and
 * attached to — the natures for the categories, the nodes, the categories and the calendars for the
 * roles —, and the server changes with one write the commands of others — the deactivation of the
 * default calendar, the reactivation of the children of a node, the deactivation and the change of
 * type of the natures and the categories of provision (#578), the change of type of the natures a
 * category leaves or joins (#577) —, which its answer does not carry. A
 * choice that would still offer an object deactivated is a command the server would refuse
 * (WF-REF-0010). The row written shows the answer meanwhile (`useAnswered`).
 */
function readAnew<T>(outcome: Outcome<T>): Outcome<T> {
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/**
 * Deactivate or reactivate an object of the reference data from the version read — none is deleted
 * (WF-REF-0010) —: the API answers the objects of its kind whose state changed — a node with its
 * descendants (WF-REF-0080) —, which take the place of their rows, and the page is read anew. A
 * reactivation makes only the object active.
 */
export async function setActivation(
  target: ActivationTarget,
  active: boolean,
): Promise<Outcome<readonly ReferenceObject[]>> {
  return readAnew(await activation(target, active));
}

/** What an object of the reference data is created from, by its kind. */
export type ReferenceCreation =
  | { readonly kind: "org_node"; readonly body: Schemas["OrgNodeWrite"] }
  | { readonly kind: "resource_role"; readonly body: Schemas["ResourceRoleWrite"] }
  | { readonly kind: "calendar"; readonly body: Schemas["CalendarWrite"] }
  | { readonly kind: "cost_type"; readonly body: Schemas["CostTypeWrite"] }
  | { readonly kind: "cost_category"; readonly body: Schemas["CostCategoryWrite"] };

/** What an object of the reference data is modified by, by its kind: the version read with it. */
export type ReferenceUpdate =
  | { readonly kind: "org_node"; readonly body: Schemas["OrgNodeUpdate"] }
  | { readonly kind: "resource_role"; readonly body: Schemas["ResourceRoleUpdate"] }
  | { readonly kind: "calendar"; readonly body: Schemas["CalendarUpdate"] }
  | { readonly kind: "cost_type"; readonly body: Schemas["CostTypeUpdate"] }
  | { readonly kind: "cost_category"; readonly body: Schemas["CostCategoryUpdate"] };

/** Ask the API to create an object of the reference data, by the operation of its kind. */
function creation(write: ReferenceCreation) {
  const client = serverClient();
  switch (write.kind) {
    case "org_node":
      return client.POST("/reference/org-nodes", { body: write.body });
    case "resource_role":
      return client.POST("/reference/resource-roles", { body: write.body });
    case "calendar":
      return client.POST("/reference/calendars", { body: write.body });
    case "cost_type":
      return client.POST("/reference/cost-types", { body: write.body });
    case "cost_category":
      return client.POST("/reference/cost-categories", { body: write.body });
  }
}

/** Ask the API to modify an object of the reference data, by the operation of its kind. */
function modification(id: string, write: ReferenceUpdate) {
  const client = serverClient();
  switch (write.kind) {
    case "org_node":
      return client.PATCH("/reference/org-nodes/{org_node_id}", {
        params: { path: { org_node_id: id } },
        body: write.body,
      });
    case "resource_role":
      return client.PATCH("/reference/resource-roles/{resource_role_id}", {
        params: { path: { resource_role_id: id } },
        body: write.body,
      });
    case "calendar":
      return client.PATCH("/reference/calendars/{calendar_id}", {
        params: { path: { calendar_id: id } },
        body: write.body,
      });
    case "cost_type":
      return client.PATCH("/reference/cost-types/{cost_type_id}", {
        params: { path: { cost_type_id: id } },
        body: write.body,
      });
    case "cost_category":
      return client.PATCH("/reference/cost-categories/{cost_category_id}", {
        params: { path: { cost_category_id: id } },
        body: write.body,
      });
  }
}

/**
 * Create an object of the reference data — a node (WF-REF-0070), a role (WF-REF-0090), a calendar
 * (WF-REF-0110), a nature (WF-REF-0030), a category (WF-REF-0040). Once the API has done it, the page
 * is read anew — the object among its lists where a list retains it: the screen adds nothing to a
 * list itself. The API answers the object created, or refuses it.
 */
export async function createReferenceObject(
  write: ReferenceCreation,
): Promise<Outcome<ReferenceObject>> {
  return readAnew(await decode<ReferenceObject>(() => creation(write)));
}

/**
 * Modify an object of the reference data from the version read — a modification affects no marked
 * revision (WF-REF-0130): the API answers the object as it now is, which takes the place of its row,
 * and the page is read anew.
 */
export async function updateReferenceObject(
  id: string,
  write: ReferenceUpdate,
): Promise<Outcome<ReferenceObject>> {
  return readAnew(await decode<ReferenceObject>(() => modification(id, write)));
}

/**
 * Designate a calendar by default (WF-REF-0120): the server withdraws the designation from the one
 * before, and changes the deactivation of both, which its answer carries for one alone — the page is
 * read anew. The contract takes no version for it.
 */
export async function designateDefaultCalendar(
  calendarId: string,
): Promise<Outcome<Schemas["Calendar"]>> {
  return readAnew(
    await decode(() =>
      serverClient().PUT("/reference/calendars/{calendar_id}/default", {
        params: { path: { calendar_id: calendarId } },
      }),
    ),
  );
}

/**
 * What the screen of the risk settings writes: the matrix alone, from the version read — never a field
 * of the other screen, which the type refuses.
 */
export type RiskMatrixWrite = Pick<
  Required<Schemas["ReferenceSettingsWrite"]>,
  "risk_matrix" | "lock_version"
> & { readonly index_thresholds?: never; readonly max_weeks_between_reviews?: never };

/**
 * What the screen of the indicator settings writes: the thresholds and the delay between two reviews
 * alone, from the version read — never the matrix, which the type refuses.
 */
export type IndicatorWrite = Pick<
  Required<Schemas["ReferenceSettingsWrite"]>,
  "index_thresholds" | "max_weeks_between_reviews" | "lock_version"
> & { readonly risk_matrix?: never };

/**
 * Write the settings of one screen of the reference data from the version read — the risk matrix
 * (WF-REF-0160), or the thresholds of the indices and the delay between two reviews (WF-REF-0170,
 * WF-REF-0180) —, never the fields of the other screen, which another permission guards
 * (WF-ADM-0100): the API answers every setting with its next version, and the page is read anew. The
 * currency (WF-REF-0140) and the default language of the installation are not written here.
 */
export async function updateReferenceSettings(
  write: RiskMatrixWrite | IndicatorWrite,
): Promise<Outcome<Schemas["ReferenceSettings"]>> {
  return readAnew(await decode(() => serverClient().PATCH("/reference/settings", { body: write })));
}
