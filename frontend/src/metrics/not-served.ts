// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The answer of the public door to the point of metrics (TFX-09, WF-SEC-0010): the metrics are
 * served on a port of their own, inside the network of the platform, and `getMetrics` declares the
 * 404 `NOT_FOUND`, without parameters, that the door gives. The ingress and Caddy send every
 * address to the front, so the front answers it, in a status Next does not soften into a screen.
 */
import type { Problem } from "@/api/problem";

/** The refusal of the contract: `NOT_FOUND`, without parameters. */
const NOT_FOUND: Problem = { code: "NOT_FOUND", status: 404 };

/** Answer a request for the metrics through the public door: 404, the envelope of the contract. */
export function metricsNotServed(): Response {
  return Response.json(NOT_FOUND, {
    status: NOT_FOUND.status,
    headers: { "Content-Type": "application/problem+json", "Cache-Control": "no-store" },
  });
}
