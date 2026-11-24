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
 * How long a slow read is waited for, in milliseconds: the measure waits so for a grid, a page
 * settled, an answer, under the load of eight users at once, where the estimate took past fifteen
 * seconds to show (`measure/steps.ts`); and a path of the service waits so for the remaining to
 * commit compared, the heaviest read of PRJ-001 (#4326).
 *
 * Measured on 2026-11-21 by `make e2e-service` on a quiet slot (`revisions.spec.ts`, the comparison
 * of the current revision of PRJ-001 to its reference): the address of the remaining to commit
 * compared 0.11 s after the click, its grid shown 3.5 s after it. In the queue, at one process of
 * the API under three workers, the same wait overran `WORKING` twice (runs 44769093797,
 * 44773195266 and 44872667894, `service / paths (2/4)`), the screen still « Chargement de l'écran »:
 * a read slowed by the load, not an error: the quiet measure is under a quarter of `WORKING`, and the
 * queue took it past it. The read is not accelerated, nothing in the measure asks it. Forty
 * seconds, eleven times the quiet measure, and less than what `test.slow` leaves of the budget of
 * the path when the wait comes: a read really degraded fails on this wait, which names the grid,
 * and not on the « Test timeout » of the whole path.
 */
export const LOADED = 40_000;

/**
 * How long the write of the default calendar and the write of the units of duration are waited for,
 * in milliseconds (`reference-resources.spec.ts`): both redate, in the request, every structure of
 * the revisions in progress (`reschedule_current_structures`). Nothing else uses it.
 *
 * Measured on 2026-11-24 by `make e2e-service` on a quiet slot: the write of the default calendar
 * took 14 to 18 s, that of the units of duration 18 to 19.5 s. Revision 102 of PRJ-001 holds nine
 * structures and about 54 000 nodes, the whole own estimate of each risk and its base, that of 752
 * included, occurred and not yet pruned. Forty seconds, twice the worst measure: the room of a
 * runner under load, which the queue gave to the reads of `LOADED` the same way, and under what
 * `test.slow` leaves of the budget of the path.
 *
 * A temporary bound, of the family below: #4874 (the own estimate kept whole in revision 102), its
 * paths listed with the others by #4911 and #4883, all corrected by US-3070/L3b (#4912), which
 * measures where the time goes and removes the family; US-3070/L4 (#4587) alone would leave
 * about seven structures in revision 102.
 */
export const REDATING = 40_000;

/*
 * The bounds of the paths that read or write revision 102 of PRJ-001 against the service, one
 * family with `REDATING`: temporary, each of them played against the service alone (the fake back
 * keeps its own bounds), and removed together by US-3070/L3b (#4912), which measures where the time
 * goes and corrects it. Revision 102 holds nine structures and about 54 000 nodes, every own
 * estimate kept whole with its base (#4874); after the switch of US-3070/L3 the paths below overran
 * their bounds in the queue, where the previous run of `epic/EP-30` (45325985235, without L3) had
 * them under (#4911). Each is measured on the workstation by `make e2e-service` (2026-11-24 and
 * 25, a platform on its own slot, four other slots busy), with the margin the queue asks for, which
 * takes two to three times the workstation. `WORKING` and `LOADED` themselves are never raised.
 */

/**
 * How long the screen of costs settings is waited for after a click of the navigation, from a
 * screen of the risks of revision 102 (`navigation.spec.ts`), in milliseconds. Measured on
 * 2026-11-25 (`make e2e-service TESTS="e2e/navigation.spec.ts --grep 'way back' --repeat-each=4"`):
 * 4.4, 4.9, 5.5 and 5.9 s, past the 5 s of an assertion twice in three on a first read. Twenty
 * seconds, three times the worst. Constat #4911.
 */
export const LEAVING_REVISION_102 = 20_000;

/**
 * What the whole path of the way back to a project is given (`navigation.spec.ts:94`), in
 * milliseconds, against the service alone, where its wait of `LEAVING_REVISION_102` may be taken
 * whole: the path took 16 s with a wait of 5 s (2026-11-24), about 11 s besides it. Sixty seconds.
 * Constat #4911.
 */
export const WAY_BACK_PATH_IN_SERVICE = 60_000;

/**
 * How long the address of the comparison of PRJ-001 to its reference is waited for after the click
 * of the base (`revisions.spec.ts`), in milliseconds. Measured on 2026-11-25
 * (`make e2e-service TESTS="e2e/revisions.spec.ts --grep 'the estimate, the cell marked' --repeat-each=3"`,
 * three at once): 14.0, 15.0 and 16.6 s, past `WORKING`; in the queue the same wait overran it
 * without L3 at 42.7 s for the whole path. Fifty seconds, three times the worst. Constat #4911.
 */
export const COMPARING_REVISION_102 = 50_000;

/**
 * What a whole path is given, in milliseconds, against the service alone: the path that enters an
 * hourly rate (`reference-costs.spec.ts:88`). Measured on 2026-11-24 and 25 by `make e2e-service`:
 * 8.4 to 12.8 s; the queue without L3 took it 12.4 s and with L3 past the 30 s of a test.
 * Forty-five seconds, three and a half times the worst. Constat #4911.
 */
export const RATE_PATH_IN_SERVICE = 45_000;

/**
 * The same for the path that names the project and the revision on each screen
 * (`context.spec.ts:34`). Measured on 2026-11-24 and 25: 12.2 to 15.5 s; the queue without L3 took it
 * 22.3 s and with L3 past 30 s. Sixty seconds, four times the worst. Constat #4911.
 */
export const CONTEXT_PATH_IN_SERVICE = 60_000;

/**
 * The same for the path that pastes a block in the own estimate of a risk
 * (`paste.spec.ts:437`), in place of the `test.slow` of the fake back, which never plays it.
 * Measured on 2026-11-24 and 25: 29.3 to 30.7 s; the queue without L3 took it 44.7 s and with L3
 * past the ninety seconds of `test.slow`. Two minutes, four times the worst. Constat #4911.
 */
export const PASTE_PATH_IN_SERVICE = 120_000;

/**
 * The same for the path that compares the estimate of PRJ-001 to its reference
 * (`revisions.spec.ts:204`), in place of its `test.slow` there. Measured on 2026-11-25, three at
 * once: 37.6 to 45.9 s; the queue without L3 took 42.7 s. Two and a half minutes, more than three
 * times the worst. Constat #4911.
 */
export const COMPARISON_PATH_IN_SERVICE = 150_000;

/**
 * The same for the two paths of the reference of the resources that redate the schedules
 * (`reference-resources.spec.ts:126` and `:300`), in place of their `test.slow` there. Measured on
 * 2026-11-25 (`--project=shared-serial`): 59.1 and 58.9 s, two writes of `REDATING` each. At worst
 * the two waits of 40 s add up, 80 s, over the ninety seconds of `test.slow` with the rest of the
 * path (about 20 s): 100 s and over, which `REDATING` alone did not budget (#4883). Two and a half
 * minutes, covers that worst case. Constat #4883, corrected by US-3070/L3b (#4912).
 */
export const REDATING_PATH_IN_SERVICE = 150_000;

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
