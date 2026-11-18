// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The window of the browsers of the measures against the service (`steps.ts`): the narrowest the
 * specification guarantees the grids usable in — 1366 points wide (WF-CMP-0010-A) — and the height
 * of a laptop of that width. Playwright's own window, 1280 × 720, is narrower than the
 * specification asks, and the real indicators of the remaining to commit — a card for the
 * difference to the reference and to the previous revision, which the fake back's do not show —
 * push the totals of its grid down: since the header of the page keeps its commands whole, under
 * the title (#3895), they end at 716.5 points in 1280 × 720 and at 742 in 1366 × 768, both in the
 * window; before it they ended at 732 or so, out of 720 once the indicators had
 * arrived: the grid was then never drawn as the measure defines it (`usable.ts`), whatever the
 * frame, while a grid opened before the indicators arrived was taken on the shorter layout of
 * their placeholder (#3801).
 */
export const MEASURE_WINDOW = { width: 1366, height: 768 } as const;
