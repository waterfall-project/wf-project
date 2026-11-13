// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The steps of a path that waits for a screen the server reads anew, timed in the browser
 * (US-1890/L3): each step, from its gesture to what it waits for, with the payloads of the screens
 * the page navigated to (`RSC`, prefetches left out) that were under way during it — asked,
 * answered, finished, or aborted by a navigation that replaced them —, all timed from the start of
 * the path, so that a payload asked by one step and still under way in the next shows as such. Each
 * step is written, as it ends, in the log of the run and in an annotation of the test, whether it
 * passed or not: the slow path of the guide measures before it corrects (« Un parcours de bout en
 * bout »), as `createOwnProject` does for the creation of a project.
 *
 * The measure of #2942 is the example: against the service, the comparison of PRJ-001 read anew
 * after « Lever le filtre » arrived in 15 s because the payload of « Comparer », asked just before,
 * was still under way, the two comparisons read together.
 */
import { type Page, type Request, test } from "@playwright/test";

/** A payload of a screen the page navigated to: its parameters, and when it reached each event. */
interface Payload {
  readonly query: string;
  readonly asked: number;
  answered?: number;
  ended?: { readonly event: string; readonly at: number };
}

/** The steps of a path, each timed and written as it ends, with the payloads under way. */
export class ScreenSteps {
  private readonly started = Date.now();
  private readonly payloads = new Map<Request, Payload>();

  constructor(
    page: Page,
    private readonly label: string,
  ) {
    page.on("request", (request) => {
      if (request.headers().rsc === "1" && request.headers()["next-router-prefetch"] !== "1") {
        const keys = [...new URL(request.url()).searchParams.keys()];
        const query = keys.filter((key) => key !== "_rsc").join(",") || "no query";
        this.payloads.set(request, { query, asked: this.since() });
      }
    });
    page.on("response", (response) => {
      const payload = this.payloads.get(response.request());
      if (payload !== undefined) {
        payload.answered = this.since();
      }
    });
    page.on("requestfinished", (request) => {
      this.end(request, "finished");
    });
    page.on("requestfailed", (request) => {
      const aborted = request.failure()?.errorText.includes("ERR_ABORTED") === true;
      this.end(request, aborted ? "aborted" : "failed");
    });
  }

  /** Run a step and time it, whether it passes or not, then write it. */
  async timed<T>(name: string, step: () => Promise<T>): Promise<T> {
    const at = this.since();
    let outcome = "";
    try {
      return await step();
    } catch (error) {
      outcome = " missed";
      throw error;
    } finally {
      this.write(`${name}${outcome} @${String(at)} ms, ${String(this.since() - at)} ms`, at);
    }
  }

  private since(): number {
    return Date.now() - this.started;
  }

  private end(request: Request, event: string): void {
    const payload = this.payloads.get(request);
    if (payload !== undefined) {
      payload.ended = { event, at: this.since() };
    }
  }

  /** Write a step, with the payloads under way during it: asked during it, or not ended before. */
  private write(step: string, from: number): void {
    const during = [...this.payloads.values()]
      .filter(({ asked, ended }) => asked >= from || ended === undefined || ended.at >= from)
      .map(({ query, asked, answered, ended }) =>
        [
          `(${query}) asked@${String(asked)}`,
          answered === undefined ? "" : ` answered@${String(answered)}`,
          ended === undefined ? " under way" : ` ${ended.event}@${String(ended.at)}`,
        ].join(""),
      );
    const measured = during.length === 0 ? step : `${step}; ${during.join("; ")}`;
    console.log(`Screen step (${this.label}): ${measured}`);
    test.info().annotations.push({ type: "screen step", description: measured });
  }
}
