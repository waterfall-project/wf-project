// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The hook Next runs once, as its server starts, before it answers a request (#825).
 *
 * The standalone server of Next writes an error `register` throws and goes on serving: the check
 * stops the process itself, after writing what is missing to the logs, and the front never answers
 * its probe (`src/startup.ts`). The settings are checked on the runtime of Node alone, which serves the
 * pages, and never while `next build` builds and prerenders them: the image is built without a
 * variable of the platform (WF-SEC-0010).
 */
import { PHASE_PRODUCTION_BUILD } from "next/constants";

/** Check the settings of the front as its server starts; fail naming what is missing. */
export async function register(): Promise<void> {
  if (process.env.NEXT_RUNTIME !== "nodejs" || process.env.NEXT_PHASE === PHASE_PRODUCTION_BUILD) {
    return;
  }
  const { checkStart } = await import("@/startup");
  checkStart();
}
