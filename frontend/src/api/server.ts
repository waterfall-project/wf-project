// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * The client of the API that server components use.
 *
 * The address comes from `WATERFALL_API_ADDRESS`: the fake back in development and in the
 * end-to-end tests, the real service from EP-03. The contract guards its operations by a
 * bearer token, which only the server of Next holds — the browser holds none (WF-ARC-0030):
 * against the service, the access token of the session of the request, found in Redis under its
 * cookie and refreshed when it expires (`src/session/tokens.ts`); `WATERFALL_AUTH=mock` is the
 * mode of the fake back, which grants the session the mock-up starts from: a fixed token
 * (`MOCK_TOKEN`). The mode is refused in a production build, except in the end-to-end
 * harness, which builds the front for production to measure it and says so with
 * `WATERFALL_E2E=1`. Nothing else tells the fake back and the real service apart.
 * Only the server of Next imports it (§4.3.1): ESLint refuses it in a client component, and
 * `server-only` fails the build of one.
 */
import "server-only";

import { requestBearer } from "@/session/tokens";

import { type ApiClient, createApiClient } from "./client";

/** The address used when none is configured: the fake back of `make mock`. */
export const DEFAULT_ADDRESS = "http://localhost:4010";

/** The token the server of Next sends in the mock mode: it opens nothing, it holds no secret. */
export const MOCK_TOKEN = "waterfall-mock-token";

/** Whether the fake back stands for the authentication (`WATERFALL_AUTH=mock`). */
export function isMockAuthentication(): boolean {
  const mode = process.env.WATERFALL_AUTH;
  if (mode === undefined || mode === "") {
    return false;
  }
  if (mode !== "mock") {
    throw new Error(`WATERFALL_AUTH must be "mock", or unset: ${mode}`);
  }
  if (process.env.NODE_ENV === "production" && process.env.WATERFALL_E2E !== "1") {
    throw new Error("WATERFALL_AUTH=mock is refused in production");
  }
  return true;
}

/**
 * Make a client of the API at the configured address: the one place that carries the token of
 * the session to the API.
 */
export function serverClient(): ApiClient {
  return createApiClient({
    address: process.env.WATERFALL_API_ADDRESS ?? DEFAULT_ADDRESS,
    bearer: isMockAuthentication() ? () => MOCK_TOKEN : requestBearer,
  });
}
