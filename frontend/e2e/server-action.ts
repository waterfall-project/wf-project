// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * How a journey recognises a write of the screens: a server action of Next, a POST that bears the
 * header `next-action`. One place to change if the way to tell one ever changes (#1872).
 */
import type { Request } from "@playwright/test";

/** Whether a request is a server action of Next, which a write of a screen is (`next-action`). */
export const isServerAction = (request: Request): boolean =>
  request.method() === "POST" && request.headers()["next-action"] !== undefined;
