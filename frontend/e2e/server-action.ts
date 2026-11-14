// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * How a journey recognises a write of the screens: a server action of Next, a POST that bears the
 * header `next-action`. One place to change if the way to tell one ever changes (#1872).
 *
 * And how it presses a command of a row whose write must leave once (`pressOnce`, #2424): pressed
 * again only while no server action has left since the first press — Playwright refused the click,
 * or React, not hydrated yet, did not take it —, never once one has, however late it leaves; the
 * answer awaited is the answer of that request, not of any action of the page (`answerOf`). A
 * command pressed again each second until its row answered asked its write twice when the answer
 * came past the second, or pressed the opposite command the answer had just put in its place
 * (#3135, #3191).
 */
import { expect, type Locator, type Page, type Request, type Response } from "@playwright/test";

import { WORKING } from "./hydration";

/** Whether a request is a server action of Next, which a write of a screen is (`next-action`). */
export const isServerAction = (request: Request): boolean =>
  request.method() === "POST" && request.headers()["next-action"] !== undefined;

/**
 * Press a command until React takes it — a server action sent —, and never once it has: the request
 * of the first action the page sends from the first press on, which this returns. The listener spans
 * every try, so that a request that leaves after the wait of its try still ends the tries. The page
 * must send no other server action meanwhile: the request is told apart by its moment alone.
 */
export async function pressOnce(page: Page, command: Locator): Promise<Request> {
  let sent: Request | undefined;
  const listen = (request: Request) => {
    if (sent === undefined && isServerAction(request)) {
      sent = request;
    }
  };
  page.on("request", listen);
  try {
    await expect(async () => {
      if (sent === undefined) {
        await command.click({ timeout: 1_000 });
      }
      await expect.poll(() => sent !== undefined, { timeout: 1_000 }).toBe(true);
    }).toPass({ timeout: WORKING });
  } finally {
    page.off("request", listen);
  }
  if (sent === undefined) {
    throw new Error("no server action left from the command pressed");
  }
  return sent;
}

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
      throw new Error(
        `no answer to ${request.method()} ${request.url()} within ${String(WORKING)} ms`,
      );
    }
    return answer;
  } finally {
    clearTimeout(timer);
  }
}
