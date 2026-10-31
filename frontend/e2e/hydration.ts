// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A page opened by its address, and the gestures that need React on it. The server renders the
 * page whole, and the browser shows it before React has hydrated it: a link followed then loads
 * its screen as a whole document, but a click on a button, a key typed in a cell, are lost — the
 * block of the navigation stays folded, the sort is never asked, and the journey waits for what
 * will never come until its end (#471). A journey opens a page here before any such gesture.
 */
import { type Locator, type Page, type Route, expect } from "@playwright/test";

/**
 * The bound of a screen of grid, in milliseconds: a dense grid — of the estimate, the planning,
 * the remaining, the risks, the actual costs, the portfolio, the reference data — or a screen that
 * reads the structure of a thousand tasks (`listNodes`) — the Kanban, the tree, the timelines —,
 * to show, to hydrate, or to read anew after a click; the comparison of two revisions too, whose
 * nodes come in the dense grid of the structures, read with `fields` (US-0500/L4, #624, #729). A
 * bound of its working under load, not a measure (#315); the risks and the actual costs, read
 * anew, overran five seconds under load: measures in #500, which is still to be decided. The
 * settings of the costs, read anew for a nature chosen, took from two to seven seconds under six
 * workers on four processors — the read of the server and the commit of the page up to four each
 * (EP-02/L41g). The probe of `openHydrated` (`indicators.spec.ts`) gives it the same bound to wait
 * for three chart buttons rendered and none hydrated, and to hold its scripts. Any other screen
 * keeps the five seconds of an assertion; the helpers below give a page that long to hydrate.
 */
export const WORKING = 15_000;

/** The cookie the shell keeps the last project context in, from an effect alone. */
const WITNESS = "wf_last_project";

/**
 * Whether React has hydrated every element of the page the keyboard can reach, read in the page:
 * React marks each element it hydrates with its props (`__reactProps$…`), a detail of its own, read
 * by the paths alone. The tools of the development server of Next live in a shadow root of their
 * own, out of reach of the search; the guards of the focus that Radix puts at the edges of the
 * document while a modal is open — the panel of the tasks, opened on a refused result — are
 * written by Radix itself, never by React, and left aside.
 */
function reachableHydrated(): boolean {
  const reachable = [
    ...document.querySelectorAll(
      ":is(a[href], button, input, select, textarea, [tabindex]):not([data-radix-focus-guard])",
    ),
  ];
  return (
    reachable.length > 0 &&
    reachable.every((element) =>
      Object.keys(element).some((key) => key.startsWith("__reactProps$")),
    )
  );
}

/**
 * Open a screen of a project by its address, and wait until the shell and the screen have
 * hydrated. The shell writes the context it shows in its cookie from an effect, so after its
 * hydration alone; the cookie of an earlier page is forgotten first, so that it cannot answer for
 * this one, and the context of a project is the path of its screen, whatever it was sorted or
 * searched by. The screen hydrates after the shell: it is rendered in the boundary of its
 * `loading.tsx`, which React hydrates on its own, once the chunks of the screen are loaded: under
 * load, the screen of the indicators hydrated up to six seconds after its title showed, and a chart
 * awaited for five seconds from the cookie was never drawn (#1537). Every element the keyboard
 * reaches, hydrated, says the screen hydrated too.
 */
export async function openHydrated(page: Page, address: string): Promise<void> {
  await page.context().clearCookies({ name: WITNESS });
  await page.goto(address);
  const shown = new URL(page.url()).pathname;
  await expect
    .poll(
      async () => {
        const cookies = await page.context().cookies();
        const witness = cookies.find(({ name }) => name === WITNESS)?.value;
        const context =
          witness === undefined ? undefined : decodeURIComponent(witness).split("?")[0];
        return { context, screen: await page.evaluate(reachableHydrated) };
      },
      { message: `the shell and the screen hydrated on ${shown}`, timeout: WORKING },
    )
    .toEqual({ context: shown, screen: true });
}

/**
 * Wait until React has hydrated every element of the page the keyboard can reach, on any screen,
 * of a project or not (`reachableHydrated`). A walk by the keyboard needs it: an element that
 * hydration renders anew drops the focus to the document, and the walk would start over.
 */
export async function untilHydrated(page: Page): Promise<void> {
  await expect
    .poll(() => page.evaluate(reachableHydrated), {
      message: `React hydrated ${new URL(page.url()).pathname}`,
      timeout: WORKING,
    })
    .toBe(true);
}

/**
 * Open or close what a button discloses — a block of the navigation, a menu, the side bar — on a
 * page that may not be hydrated yet: no project is opened there, and nothing witnesses its
 * hydration. The button is pressed only while it does not say the state asked, so a press that
 * React answered is never undone, and pressed again until it says it.
 */
export async function setExpanded(button: Locator, expanded: boolean): Promise<void> {
  const state = String(expanded);
  await expect(async () => {
    if ((await button.getAttribute("aria-expanded")) !== state) {
      await button.click();
    }
    await expect(button).toHaveAttribute("aria-expanded", state, { timeout: 1_000 });
  }).toPass({ timeout: WORKING });
}

/**
 * Open a menu on a page that may not be hydrated yet, by the button that opens it: pressed only
 * while the menu is not shown, and again until it is. A menu hides the rest of the page from the
 * tree of accessibility while it is open, its button with it: it is the menu that says it opened.
 */
export async function openMenu(button: Locator, menu: Locator): Promise<void> {
  await expect(async () => {
    if (!(await menu.isVisible())) {
      await button.click();
    }
    await expect(menu).toBeVisible({ timeout: 1_000 });
  }).toPass({ timeout: WORKING });
}

/**
 * Sort a dense grid by a column, ascending, on a page that may not be hydrated yet, with nothing
 * to witness it, and wait for the address of the sort. The button of the header is pressed only
 * while the header does not say it is sorted so — the grid shows a sort asked at once, before the
 * server answers — nor the grid busy reading, and again until the address says it. A sort is never
 * pressed blind: a press React answered and pressed again would turn it to descending.
 */
export async function sortUntilAddress(
  header: Locator,
  grid: Locator,
  address: string,
): Promise<void> {
  const page = header.page();
  await expect(async () => {
    const [sorted, busy] = await Promise.all([
      header.getAttribute("aria-sort"),
      grid.getAttribute("aria-busy"),
    ]);
    if (sorted !== "ascending" && busy !== "true") {
      await header.getByRole("button").click();
    }
    await expect(page).toHaveURL(address, { timeout: 1_000 });
    // The time to hydrate, then to read the grid anew: two bounds.
  }).toPass({ timeout: 2 * WORKING });
}

/** The scripts of the front, which a screen hydrates once loaded. */
const SCRIPTS = "**/_next/static/chunks/**";

/**
 * A script fetched for the page on a connection of its own: one kept open across a held script
 * was closed by the front as idle while the journey reused it (ECONNRESET, under load).
 */
const ONE_USE = { connection: "close" };

/** A script the route of `holdScripts` caught: its address, and its body as the front serves it. */
export interface CaughtScript {
  readonly url: string;
  readonly body: Buffer;
}

/** The route of `holdScripts`, posed: `remove` takes it away once the scripts it caught are served. */
export interface HeldScripts {
  remove(): Promise<void>;
}

/**
 * Whether Playwright has handled a route already: it hands a request the route caught on to the
 * network when the interception of the page is taken away under it, and the handler's own answer
 * then fails with this message, which no type of error tells (#1635).
 */
function handledAlready(error: unknown): boolean {
  return error instanceof Error && error.message.includes("Route is already handled");
}

/**
 * Hold the scripts of the front a journey picks, so that a screen hydrates when the journey lets
 * it, whatever the load: each script the page asks for is fetched, given to `hold` with its body,
 * and served once what `hold` returns has settled — at once for a script it does not pick.
 *
 * The route closes its race with the page (#1635). Playwright gives up the interception of the
 * page as soon as a handler ends with no route left, and hands every request still caught to the
 * network: the handlers still in flight then answer a request already answered, and fail with
 * « Route is already handled ». `page.unrouteAll({ behavior: "wait" })` did so whenever two
 * scripts were in flight as it was called — the scripts a screen loads once hydrated, asked for as
 * the journey ends —, and waiting for the network to be idle first only narrowed the window. So
 * `remove` waits for every handler in flight before it takes the route away, a script asked for
 * meanwhile let go to the network unheld; and a handler whose route was answered already all the
 * same — the interception taken away by another hand — lets it go, the network having served it.
 * A handler that fails does not keep the route posed: `remove` takes it away whatever they end in.
 * (`route.fallback()` needs no such guard: in playwright-core 1.64 it is a call of the client
 * alone, which throws « Route is already handled » only when this very route was answered through
 * the client already, never because the interception was taken away; the continue that follows it
 * ignores its own failure.)
 */
export async function holdScripts(
  page: Page,
  hold: (script: CaughtScript) => Promise<void> | void,
): Promise<HeldScripts> {
  const inFlight = new Set<Promise<void>>();
  let removing = false;
  const serve = async (route: Route): Promise<void> => {
    if (removing) {
      await route.fallback();
      return;
    }
    const url = route.request().url();
    const response = await page.request.get(url, { headers: ONE_USE });
    await hold({ url, body: await response.body() });
    try {
      await route.fulfill({ response });
    } catch (error) {
      if (!handledAlready(error)) {
        throw error;
      }
      await route.fallback();
    }
  };
  const handler = (route: Route): Promise<void> => {
    const served = serve(route);
    inFlight.add(served);
    const settled = (): void => {
      inFlight.delete(served);
    };
    served.then(settled, settled);
    return served;
  };
  await page.route(SCRIPTS, handler);
  return {
    async remove(): Promise<void> {
      removing = true;
      // Settled, not all: a handler that fails (a `hold` that throws) is not the removal's to
      // report, and the route is taken away all the same.
      while (inFlight.size > 0) {
        await Promise.allSettled([...inFlight]);
      }
      await page.unroute(SCRIPTS, handler);
    },
  };
}
