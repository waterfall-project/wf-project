// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The route that holds the scripts of the front (`holdScripts`, `hydration.ts`), held to its race
 * with the page (#1635): a script asked for after the last silence of the network and before the
 * route is taken away. The race is given, not waited for: each script is asked for by the test, on
 * an address of its own that no cache answers, and held by the test until it lets it go — whatever
 * the load, the handlers are in flight in the order the test says.
 *
 * This tests a tool of the harness: it proves no requirement of the specification.
 */
import { expect, type Page, type Route, test } from "@playwright/test";

import { holdScripts } from "./hydration";

/** A script held by the test: `caught` once the route has it, served once `open` is called. */
interface Gate {
  readonly caught: Promise<void>;
  readonly opened: Promise<void>;
  take(): void;
  open(): void;
}

function gate(): Gate {
  let caught = (): void => undefined;
  let open = (): void => undefined;
  return {
    caught: new Promise<void>((resolve) => {
      caught = resolve;
    }),
    opened: new Promise<void>((resolve) => {
      open = resolve;
    }),
    take: () => {
      caught();
    },
    open: () => {
      open();
    },
  };
}

/** Two scripts of the home the front serves, opened, read from the page. */
async function twoScripts(page: Page): Promise<readonly [string, string]> {
  await page.goto("/");
  const [one, two] = await page.evaluate(() =>
    [...document.scripts]
      .map(({ src }) => src)
      .filter((src) => src.includes("/_next/static/chunks/")),
  );
  if (one === undefined || two === undefined) {
    throw new Error("the home loads two scripts of the front at least");
  }
  return [one, two];
}

/** Have the page load a script, as it loads its own, and say whether it was served. */
function ask(page: Page, url: string): Promise<"loaded" | "failed"> {
  return page.evaluate(
    (address) =>
      new Promise<"loaded" | "failed">((resolve) => {
        const script = document.createElement("script");
        script.src = address;
        script.addEventListener("load", () => {
          resolve("loaded");
        });
        script.addEventListener("error", () => {
          resolve("failed");
        });
        document.head.append(script);
      }),
    url,
  );
}

test("takes its route away once the scripts in flight are served, two asked for after the last silence and before the removal, one served before the other (#1635)", async ({
  page,
}) => {
  // Each under an address of its own, which no cache has answered.
  const [one, two] = await twoScripts(page);
  const [first, second, after] = [`${one}?held=first`, `${two}?held=second`, `${one}?held=after`];
  const gates = new Map([
    [first, gate()],
    [second, gate()],
  ]);
  const caught: string[] = [];
  const scripts = await holdScripts(page, async ({ url }) => {
    caught.push(url);
    const held = gates.get(url);
    held?.take();
    await held?.opened;
  });
  // Two scripts asked for, both caught by the route before it is taken away.
  const servedFirst = ask(page, first);
  const servedSecond = ask(page, second);
  await Promise.all([...gates.values()].map(({ caught: held }) => held));
  // `remove` taking the route away is seen at `page.unroute`, not guessed from the order of replies.
  let unrouted = false;
  const unroute = page.unroute.bind(page);
  page.unroute = ((...args: Parameters<Page["unroute"]>) => {
    unrouted = true;
    return unroute(...args);
  }) as Page["unroute"];
  const removal = scripts.remove();
  // The first served while the second is still held: the route stays for the second.
  gates.get(first)?.open();
  expect(await servedFirst).toBe("loaded");
  expect(unrouted).toBe(false);
  gates.get(second)?.open();
  expect(await servedSecond).toBe("loaded");
  await removal;
  expect(unrouted).toBe(true);
  // Taken away: a script asked for now goes to the network, uncaught.
  expect(await ask(page, after)).toBe("loaded");
  expect(caught).not.toContain(after);
});

test("lets go a script whose route was answered already, the interception of the page taken away under it (#1635)", async ({
  page,
}) => {
  const [one] = await twoScripts(page);
  const script = `${one}?held=taken`;
  const held = gate();
  const scripts = await holdScripts(page, async ({ url }) => {
    if (url === script) {
      held.take();
      await held.opened;
    }
  });
  const served = ask(page, script);
  await held.caught;
  // Another hand takes every route of the page away: Playwright hands the script on to the
  // network, and the route answers a request already answered.
  await page.unrouteAll();
  held.open();
  expect(await served).toBe("loaded");
  await scripts.remove();
});

test("takes its route away although a hold failed, and does not report the failure (#1635)", async () => {
  // Playwright makes the error of a route handler the test's own, so the page is a double here:
  // the handler is called as Playwright calls it, and the removal is seen at `unroute`.
  let posed: ((route: Route) => Promise<void>) | undefined;
  let unrouted = false;
  const double = {
    route: (_pattern: string, handler: (route: Route) => Promise<void>) => {
      posed = handler;
      return Promise.resolve();
    },
    unroute: () => {
      unrouted = true;
      return Promise.resolve();
    },
    request: {
      get: () => Promise.resolve({ body: () => Promise.resolve(Buffer.from("")) }),
    },
  };
  const route = { request: () => ({ url: () => "http://front/_next/static/chunks/a.js" }) };
  const failing = gate();
  const scripts = await holdScripts(double as unknown as Page, async () => {
    failing.take();
    await failing.opened;
    throw new Error("a hold that fails");
  });
  const handled = posed?.(route as unknown as Route);
  await failing.caught;
  // The removal waits for a handler in flight, which then fails.
  const removal = scripts.remove();
  failing.open();
  await expect(handled).rejects.toThrow("a hold that fails");
  await removal;
  expect(unrouted).toBe(true);
});
