// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/**
 * Set up every unit test of the front.
 *
 * `src/api/client.ts` and `server.ts` import `server-only`, which throws anywhere but in the
 * server bundle of Next: the net of `next build` under the rule of ESLint that keeps a
 * client component from importing them. A test is not that bundle, so the marker is
 * emptied here; a test that checks the refusal restores it with `vi.doUnmock`.
 */
import { vi } from "vitest";

vi.mock("server-only", () => ({}));
