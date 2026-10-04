// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The server actions of the reference data — a cell of the grid of the hourly rates entered
 * (`setHourlyRate`) —: the grid asks the server of Next, which calls the API (§4.3.1), and gets
 * back the outcome the one decoder makes of its answer (`src/api/problem.ts`).
 */
"use server";

import type { components } from "@/api/generated/schema";
import { decode, type Outcome } from "@/api/problem";
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
