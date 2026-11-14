// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * How a journey recognises a write of the screens: a server action of Next, a POST that bears the
 * header `next-action`. One place to change if the way to tell one ever changes (#1872).
 *
 * And how it presses a command of a row whose write must leave once (`pressOnce`, #2424): pressed
 * again only while the action it asks has not left — Playwright refused the click, or React, not
 * hydrated yet, did not take it, or took it and sent nothing within the wait of the try —, never
 * once it has; the action is told by its request itself, its body, not by its moment, and the
 * answer awaited is the answer of that request, not of any action of the page (`answerOf`). A
 * command pressed again each second until its row answered asked its write twice when the answer
 * came past the second, or pressed the opposite command the answer had just put in its place
 * (#3135, #3191). The window left: a request that leaves past the wait of the try after a click
 * Playwright did accept (`TAKEN`) still comes after a second press.
 */
import { expect, type Locator, type Page, type Request, type Response } from "@playwright/test";

import { WORKING } from "./hydration";

/** Whether a request is a server action of Next, which a write of a screen is (`next-action`). */
export const isServerAction = (request: Request): boolean =>
  request.method() === "POST" && request.headers()["next-action"] !== undefined;

/** How long a try waits for the action after a click Playwright accepted: React may be slow to send. */
const TAKEN = 4_000;
/** How long it waits after a click that failed: the next try presses again. */
const REFUSED = 1_000;

/**
 * Press a command until React takes it — the action it asks sent —, and never once it has: the
 * first request of a server action that `asked` recognises, from the first press on, which this
 * returns. `asked` reads the request, its body (`postData()`), so that an action the page sends of
 * itself — the preferences of a grid kept on hydration — is never taken for the command. The
 * listener spans every try, so that a request that leaves after the wait of its try still ends the
 * tries.
 */
export async function pressOnce(
  page: Page,
  command: Locator,
  asked: (request: Request) => boolean,
): Promise<Request> {
  let sent: Request | undefined;
  const listen = (request: Request) => {
    if (sent === undefined && isServerAction(request) && asked(request)) {
      sent = request;
    }
  };
  page.on("request", listen);
  try {
    await expect(async () => {
      if (sent !== undefined) {
        return;
      }
      let wait = REFUSED;
      try {
        await command.click({ timeout: 1_000 });
        wait = TAKEN;
      } catch {
        // Refused by Playwright: no action can have left from this press, the next try presses again.
      }
      await expect.poll(() => sent !== undefined, { timeout: wait }).toBe(true);
    }).toPass({ timeout: WORKING });
  } finally {
    page.off("request", listen);
  }
  if (sent === undefined) {
    throw new Error("no server action asked left from the command pressed");
  }
  return sent;
}

/**
 * Whether a request is the deactivation of an object (`setActivation(target, false)`): the body of
 * the action holds the target and the state asked, `[{"kind":…,"id":…,…},false]`.
 */
export const isDeactivation = (request: Request): boolean =>
  /^\[\{[^\]]*"kind":"[a-z_]+"[^\]]*\},false\]$/.test(request.postData() ?? "");

/** The answer of a request, awaited within `WORKING`: that of this request, and of no other. */
export async function answerOf(request: Request): Promise<Response> {
  let timer: ReturnType<typeof setTimeout> | undefined;
  const late = new Promise<null>((resolve) => {
    timer = setTimeout(() => {
      resolve(null);
    }, WORKING);
  });
  try {
    const answer = await Promise.race([request.response(), late]);
    if (answer === null) {
      const failure = request.failure();
      throw new Error(
        failure === null
          ? `no answer to ${request.method()} ${request.url()} within ${String(WORKING)} ms`
          : `${request.method()} ${request.url()} failed: ${failure.errorText}`,
      );
    }
    return answer;
  } finally {
    clearTimeout(timer);
  }
}
