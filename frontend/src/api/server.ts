// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The client of the API that server components use.
 *
 * The address comes from `WATERFALL_API_ADDRESS`: the fake back in development and in the
 * end-to-end tests, the real service from EP-03. Nothing else tells them apart.
 * `server-only`: a client component that imported it would not build (§4.3.1).
 */
import "server-only";

import { type ApiClient, createApiClient } from "./client";

/** The address used when none is configured: the fake back of `make mock`. */
export const DEFAULT_ADDRESS = "http://localhost:4010";

/** Make a client of the API at the configured address. */
export function serverClient(): ApiClient {
  return createApiClient({ address: process.env.WATERFALL_API_ADDRESS ?? DEFAULT_ADDRESS });
}
