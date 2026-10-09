// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the reference data — a cell of the grid of the hourly rates entered
 * (`setHourlyRate`), an object deactivated reactivated (`reactivate`), a nature or a category of
 * cost created, modified, deactivated or reactivated (`createCostObject`, `updateCostObject`,
 * `setCostActivation`) —: the screen asks the server of Next, which calls the API (§4.3.1), and gets
 * back the outcome the one decoder makes of its answer (`src/api/problem.ts`).
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

/** A nature or a category of cost, which may be deactivated and reactivated (WF-REF-0010). */
type CostTarget = ActivationTarget & { readonly kind: "cost_type" | "cost_category" };

/** Ask the API to activate or deactivate a nature or a category, from the version read. */
function costActivation(target: CostTarget, active: boolean) {
  const client = serverClient();
  const body = { is_active: active, lock_version: target.lockVersion };
  return target.kind === "cost_type"
    ? client.PUT("/reference/cost-types/{cost_type_id}/activation", {
        params: { path: { cost_type_id: target.id } },
        body,
      })
    : client.PUT("/reference/cost-categories/{cost_category_id}/activation", {
        params: { path: { cost_category_id: target.id } },
        body,
      });
}

/** Ask the API to activate or deactivate an object, by the operation of its kind, from the version read. */
function activation(target: ActivationTarget, active: boolean) {
  const client = serverClient();
  const body = { is_active: active, lock_version: target.lockVersion };
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
    case "cost_category":
      return costActivation({ ...target, kind: target.kind }, active);
  }
}

/**
 * Reactivate an object of the reference data a list shows deactivated (WF-REF-0150), from the
 * version read: once the API has done it, the page is rendered again, and reads the list anew —
 * the object active, and what the server reactivated with it. Nothing is deleted nor deactivated
 * here.
 */
export async function reactivate(target: ActivationTarget): Promise<Settled> {
  const outcome = await decode<unknown>(() => activation(target, true));
  if (outcome.kind === "done") {
    refresh();
  }
  return settled(outcome);
}

/** A nature or a category of cost, as the server answers a write of it. */
export type CostObject = components["schemas"]["CostType"] | components["schemas"]["CostCategory"];

/** What a nature or a category of cost is created from, by its kind. */
export type CostCreation =
  | { readonly kind: "cost_type"; readonly body: components["schemas"]["CostTypeWrite"] }
  | { readonly kind: "cost_category"; readonly body: components["schemas"]["CostCategoryWrite"] };

/** What a nature or a category of cost is modified by, by its kind: the version read with it. */
export type CostUpdate =
  | { readonly kind: "cost_type"; readonly body: components["schemas"]["CostTypeUpdate"] }
  | {
      readonly kind: "cost_category";
      readonly body: components["schemas"]["CostCategoryUpdate"];
    };

/** Ask the API to create a nature or a category of cost. */
function creation(write: CostCreation) {
  const client = serverClient();
  return write.kind === "cost_type"
    ? client.POST("/reference/cost-types", { body: write.body })
    : client.POST("/reference/cost-categories", { body: write.body });
}

/**
 * Read the page anew once a nature or a category is written: the natures are what the categories are
 * filtered on and attached to, the categories of labour the rows of the grid of the rates — a choice
 * that would still offer a nature deactivated, or name one by its former label, is a command the
 * server would refuse (WF-REF-0010). The row written shows the answer meanwhile (`useAnswered`).
 */
function readAnew<T>(outcome: Outcome<T>): Outcome<T> {
  if (outcome.kind === "done") {
    refresh();
  }
  return outcome;
}

/**
 * Create a nature (WF-REF-0030) or a category of cost (WF-REF-0040). Once the API has done it, the
 * page is read anew — the object among its lists where a list retains it: the screen adds nothing to
 * a list itself. The API answers the object created, or refuses it.
 */
export async function createCostObject(write: CostCreation): Promise<Outcome<CostObject>> {
  return readAnew(await decode<CostObject>(() => creation(write)));
}

/**
 * Modify a nature or a category of cost from the version read — a modification affects no marked
 * revision (WF-REF-0130): the API answers the object as it now is, which takes the place of its row,
 * and the page is read anew.
 */
export async function updateCostObject(
  id: string,
  write: CostUpdate,
): Promise<Outcome<CostObject>> {
  const client = serverClient();
  return readAnew(
    await decode<CostObject>(() =>
      write.kind === "cost_type"
        ? client.PATCH("/reference/cost-types/{cost_type_id}", {
            params: { path: { cost_type_id: id } },
            body: write.body,
          })
        : client.PATCH("/reference/cost-categories/{cost_category_id}", {
            params: { path: { cost_category_id: id } },
            body: write.body,
          }),
    ),
  );
}

/**
 * Deactivate or reactivate a nature or a category of cost from the version read — none is deleted
 * (WF-REF-0010): the API answers the object as it now is, which takes the place of its row, and the
 * page is read anew.
 */
export async function setCostActivation(
  target: CostTarget,
  active: boolean,
): Promise<Outcome<CostObject>> {
  return readAnew(await decode<CostObject>(() => costActivation(target, active)));
}
