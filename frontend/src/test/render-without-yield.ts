// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * A render of a component test never yields to the browser, whatever the speed of the machine.
 *
 * React renders the transitions in slices, and asks its scheduler whether the slice is spent. In a
 * test, the scheduler runs next to no task of its own — React flushes its work in `act` —, so the
 * time it counts from the last of them only grows, and past 5 ms a render yields. Inside the `act`
 * of an event, which is not awaited (`fireEvent`, `userEvent`), the work left pending on yielding
 * is what React reports as « A component suspended inside an `act` scope, but the `act` call was
 * not awaited »: a test failed by the load of the machine, coverage and the other tests running at
 * once, not by the code (#4000). With no yield, `act` ends with its work done, as it does on a fast
 * machine.
 *
 * Loaded before React (`src/test/setup-dom.ts`): `react-dom` keeps the function it finds then.
 */
import { createRequire } from "node:module";

interface Scheduler {
  unstable_shouldYield: () => boolean;
}

const requireFromReact = createRequire(createRequire(import.meta.url).resolve("react-dom"));
const scheduler = requireFromReact("scheduler") as Scheduler;
scheduler.unstable_shouldYield = () => false;
