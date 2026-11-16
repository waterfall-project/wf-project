// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The bounds of time of the paths, in one place (US-2290): what a path waits for a screen of grid
 * and for the marking of a revision, against the fake back as against the service, and why. A
 * bound is one of the working of a path under load, never a measure: the measures are those of
 * `make measure` and of the queue, quoted below, and a bound that a path overruns is first a read
 * to correct, then a path to isolate, and only last a bound to widen, the measure in the comment
 * that widens it (the guide, « Un parcours lent »). The measures keep bounds of their own, far from
 * what they measure (`usable.ts`, `measure/steps.ts`).
 */

/**
 * The bound of a screen of grid, in milliseconds: a dense grid — of the estimate, the planning,
 * the remaining, the risks, the actual costs, the portfolio, the reference data — or a screen that
 * reads the structure of a thousand tasks (`listNodes`) — the Kanban, the tree, the timelines —,
 * to show, to hydrate, or to read anew after a click — a sort, a filter, a search, whose address
 * the browser shows only once the server has rendered the screen anew, every read of the page
 * awaited —; the comparison of two revisions too, whose nodes come in the dense grid of the
 * structures, read with `fields` (US-0500/L4, #624, #729). The probe of `openHydrated`
 * (`indicators.spec.ts`) gives it the same bound to wait for three chart buttons rendered and none
 * hydrated, and to hold its scripts. Any other screen keeps the five seconds of an assertion on a
 * workstation, ten in the chain (`playwright.config.ts`).
 *
 * Measured on PRJ-001, the witness of a thousand tasks, the heaviest project the paths read:
 *
 * - in the queue, at one process of the API, the screen read anew overran it: the remaining to
 *   commit filtered by a post (`structure.spec.ts`) kept its address past fifteen seconds twice,
 *   in 43407154031 and 43506348736 (2026-11-13), the filtered nodes asked of the API at once but
 *   the indicators of the page (`getRemainingIndicators`) answered in 24.3 and 15.7 s, beside a
 *   comparison of PRJ-001 of 12.5 to 17.9 s, all on the one core of the API (#3087);
 * - on a workstation, at one process, eight users reading it at once took 16.4 s in the median to
 *   reach the remaining from the estimate, 18.1 s at worst (`docs/measures/processes.json`): the
 *   load of the queue then, three workers on the one core of the API;
 * - at four processes (US-2230) and the reads corrected (US-2220, US-2250, US-2270), by
 *   `make measure` on 2026-11-16 (epic/EP-26 at f27b3365, five passes), the slowest step of the
 *   journey took at worst 1.4 s for one user, 3.4 s for four and 6.4 s for eight — the duration
 *   entered in the planning —, the remaining reached from the estimate 1.0, 2.6 and 4.5 s;
 * - in the queue since, at four processes on the four processors of a runner and three workers
 *   (`service.yml`), no path of PRJ-001 failed on it in the runs of epic/EP-26 from 43689662405 to
 *   43883924367.
 *
 * Fifteen seconds stay: more than twice the worst step at eight users, the load of the queue
 * measured at one process, where a screen read anew had overrun it.
 */
export const WORKING = 15_000;

/**
 * How long the worker is given to mark a revision: a task taken from the queue, one transaction.
 *
 * Measured on 2026-11-16 by `make measure-version MEASURE_VERSION=0.4.0` (US-2300, fifty users of
 * load, three passes), each pass read from the submission of the task to its end
 * (`getBackgroundTask`): a median of 0.101 s and a worst of 0.240 s (`mark-revision` of
 * `docs/measures/0.4.0.json`). The minute covers them with a wide margin, 250 times the worst:
 * it is the room a task waiting in the queue is given to be taken by the worker, not a duration
 * of the marking itself.
 */
export const MARKING = 60_000;

/*
 * The budgets of the paths themselves, below: what a whole test is given, or a wait that is not the
 * showing of a screen of PRJ-001 (`WORKING`). None is a measure; a path that overruns one is first
 * a read to correct, as the header says, and none of them has been measured on its own.
 */

/**
 * How long Tab alone is given to reach the one stop of a grid, in milliseconds
 * (`keyboard.spec.ts`, `entry.spec.ts`): each press is a round trip to the browser, through the
 * shell and the bar of the grid (beside `test.slow`). Twice `WORKING`.
 */
export const TABBING = 30_000;

/**
 * How long a path that opens the planning of a thousand tasks is given, whole, in milliseconds:
 * `opening.spec.ts` opens each grid of it several times and counts what it sends, and
 * `departure.spec.ts` slows the processor four times (US-0800) to leave it for another screen. Each
 * opening is bounded by its own wait, this is the sum of those a path makes; twelve times `WORKING`.
 */
export const OPENING_PATH = 180_000;

/**
 * How long the reset of the grids of an account is given, whole, in milliseconds
 * (`service/grid-reset.spec.ts`): the administrator of the installation signed in, an account
 * created and signed in at the identity provider, three tokens, two writes and two reads of its
 * preferences. No screen of grid, none of the thousand tasks: six times `WORKING`, for the sign-ins
 * of a runner under load.
 */
export const ACCOUNT_RESET = 90_000;

/**
 * How long a path of fifty entries each undone, then redone, is given, whole, in milliseconds
 * (`undo.spec.ts`, the planning and the estimate): a screen of grid under load takes its `WORKING`
 * bound for each of them, a hundred waits in all. It is a budget under the sum of those bounds
 * (twenty-five minutes), which only a path where every wait overran would reach.
 */
export const FIFTY_ENTRIES_UNDONE = 20 * 60_000;
