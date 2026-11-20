// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * What the front counts of its requests, in the format of Prometheus (WF-OBS-0010): how many, by
 * kind and status, and how long each took. The error rate is the share of those answered with a
 * status of 500 or more, as the API's (`waterfall_api_requests_total`): the rules of the alerts
 * (US-2880) compute it from these two series.
 *
 * The names are the interface, as the API's are (`backend/src/waterfall/platform/metrics.py`). No
 * label carries what a request holds: a request is named by its kind — a page, a server action, a
 * static asset — and never by its path, which holds identifiers of projects; no identity, no
 * secret (TFX-09).
 */
import { Counter, Histogram, Registry } from "@prometheus-io/client";

/** The requests served, by kind and status. */
export const REQUESTS = "waterfall_front_requests_total";
/** The time taken to answer a request, by kind. */
export const REQUEST_DURATION = "waterfall_front_request_duration_seconds";

/** What a request asks for: a screen, a server action, or a file of the build. */
export type RequestKind = "page" | "action" | "asset";

/** The type of the exposition: the text format every version of Prometheus reads. */
export const CONTENT_TYPE = "text/plain; version=0.0.4; charset=utf-8";

/** The kind of a request, from its path and whether it carries the header of a server action. */
export function requestKind(path: string, isAction: boolean): RequestKind {
  if (path.startsWith("/_next/")) {
    return "asset";
  }
  return isAction ? "action" : "page";
}

/** The registry of the front and the series it holds. */
export class FrontMetrics {
  readonly registry = new Registry();
  private readonly requests = new Counter({
    name: REQUESTS,
    help: "Requests served, by kind (page, action or asset) and status of the answer.",
    labelNames: ["kind", "status"],
    registers: [this.registry],
  });
  private readonly durations = new Histogram({
    name: REQUEST_DURATION,
    help: "Time taken to answer a request, by kind.",
    labelNames: ["kind"],
    registers: [this.registry],
  });

  /** Count a request answered under its kind and status, and how long it took. */
  requestEnded(kind: RequestKind, status: number, seconds: number): void {
    this.requests.inc({ kind, status: String(status) });
    this.durations.observe({ kind }, seconds);
  }

  /** The metrics in the text format of Prometheus (`CONTENT_TYPE`). */
  expose(): Promise<string> {
    return this.registry.metrics();
  }
}
