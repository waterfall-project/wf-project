// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Set up every unit test of the front.
 *
 * `src/api/client.ts` and `server.ts` import `server-only`, which throws anywhere but in the
 * server bundle of Next: that is what keeps a client component from calling the API. A
 * test is not that bundle, so the marker is emptied here; a test that checks the refusal
 * restores it with `vi.doUnmock`.
 */
import { vi } from "vitest";

vi.mock("server-only", () => ({}));
