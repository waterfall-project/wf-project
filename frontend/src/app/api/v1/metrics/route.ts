// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/** `getMetrics` on the public door, `/api/v1/metrics`: not served (`src/metrics/not-served.ts`). */
import { metricsNotServed } from "@/metrics/not-served";

export const GET = metricsNotServed;
