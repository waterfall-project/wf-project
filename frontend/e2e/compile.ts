// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Routes a path reaches by a click, compiled before the path starts. The development server
 * compiles a route the first time it is asked for, its client chunks with it; a route reached by
 * a click is then awaited by an assertion bounded to five seconds, which the compilation eats —
 * all of it on a first run, `.next` cold and four workers compiling at once (#142). Asked for
 * here, the route compiles within the time of the test, as a route opened by `page.goto` does.
 */
import { type APIRequestContext, expect } from "@playwright/test";

/**
 * Have the development server compile routes, all at once, each answered as a page is: redirects
 * followed.
 */
export async function compile(request: APIRequestContext, ...routes: string[]): Promise<void> {
  const responses = await Promise.all(routes.map((route) => request.get(route)));
  responses.forEach((response, index) => {
    expect(response.ok(), routes[index]).toBe(true);
  });
}

/**
 * Have the development server compile routes that answer a request without a session otherwise
 * than a page: a redirect not followed, a method refused, a screen that asks for a session. Any
 * answer but an error of the server.
 */
export async function compileAnswered(
  request: APIRequestContext,
  ...routes: string[]
): Promise<void> {
  const responses = await Promise.all(
    routes.map((route) => request.get(route, { maxRedirects: 0 })),
  );
  responses.forEach((response, index) => {
    expect(response.status(), routes[index]).toBeLessThan(500);
  });
}
