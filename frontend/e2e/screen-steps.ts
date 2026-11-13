// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The steps of a path that waits for a screen the server reads anew, timed in the browser
 * (US-1890/L3): each step, from its gesture to what it waits for, and every payload of a screen the
 * page asked (`RSC`) — asked, answered, finished, or aborted by a navigation that replaced it —, all
 * timed from the start of the path, so that a payload asked by one step and still under way in the
 * next shows as such. Written in the log of the run and in an annotation of the test, whether the
 * path passed or not: the slow path of the guide measures before it corrects (« Un parcours de bout
 * en bout »), as `createOwnProject` does for the creation of a project.
 */
import { type Page, type Request, type Response, test } from "@playwright/test";

/** The steps of a path, each timed, and the payloads of the screens the page asked. */
export class ScreenSteps {
  private readonly started = Date.now();
  private readonly done: string[] = [];
  private readonly payloads = new Map<Request, string[]>();
  private readonly onRequest = (request: Request): void => {
    this.note(request, "asked");
  };
  private readonly onResponse = (response: Response): void => {
    this.note(response.request(), "answered");
  };
  private readonly onFinished = (request: Request): void => {
    this.note(request, "finished");
  };
  private readonly onFailed = (request: Request): void => {
    const cancelled = request.failure()?.errorText.includes("ERR_ABORTED") === true;
    this.note(request, cancelled ? "aborted" : "failed");
  };

  constructor(
    private readonly page: Page,
    private readonly label: string,
  ) {
    page.on("request", this.onRequest);
    page.on("response", this.onResponse);
    page.on("requestfinished", this.onFinished);
    page.on("requestfailed", this.onFailed);
  }

  /** Run a step and time it, whether it passes or not: from when it started, how long it took. */
  async timed<T>(name: string, step: () => Promise<T>): Promise<T> {
    const at = this.since();
    let outcome = "";
    try {
      return await step();
    } catch (error) {
      outcome = " missed";
      throw error;
    } finally {
      this.done.push(`${name}${outcome} @${String(at)} ${String(this.since() - at)} ms`);
    }
  }

  /** Write the steps and the payloads, in the log and in an annotation; the listeners are removed. */
  report(): void {
    this.page.off("request", this.onRequest);
    this.page.off("response", this.onResponse);
    this.page.off("requestfinished", this.onFinished);
    this.page.off("requestfailed", this.onFailed);
    const payloads = [...this.payloads.values()].map((events) => events.join(" "));
    const measured =
      `${this.done.join("; ")}; payloads: ${payloads.join("; ") || "none"}; ` +
      `total ${String(this.since())} ms`;
    console.log(`Screen steps (${this.label}): ${measured}`);
    test.info().annotations.push({ type: "screen steps", description: measured });
  }

  private since(): number {
    return Date.now() - this.started;
  }

  /** An event of a payload of a screen, named by the parameters of its address. */
  private note(request: Request, event: string): void {
    if (request.headers().rsc !== "1") {
      return;
    }
    let events = this.payloads.get(request);
    if (events === undefined) {
      const keys = [...new URL(request.url()).searchParams.keys()].filter((key) => key !== "_rsc");
      const prefetch = request.headers()["next-router-prefetch"] === undefined ? "" : "prefetch ";
      events = [`(${prefetch}${keys.join(",") || "no query"})`];
      this.payloads.set(request, events);
    }
    events.push(`${event}@${String(this.since())}`);
  }
}
