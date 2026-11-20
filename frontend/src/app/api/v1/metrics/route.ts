// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/** `getMetrics` on the public door, `/api/v1/metrics`: not served (`src/metrics/not-served.ts`). */
import { metricsNotServed } from "@/metrics/not-served";

// Every method gets the 404 of the contract, not the 405 Next gives a method a route does not name.
export const GET = metricsNotServed;
export const HEAD = metricsNotServed;
export const POST = metricsNotServed;
export const PUT = metricsNotServed;
export const PATCH = metricsNotServed;
export const DELETE = metricsNotServed;
export const OPTIONS = metricsNotServed;
