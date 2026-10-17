// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The client of the front is the one the contract produces (US-0020, WF-ARC-0060): its types,
 * `generated/schema.d.ts`, are generated again here from the contract, by the generator
 * `make generate-client` runs and with its settings, and the versioned file must be what it
 * writes, byte for byte — a change made by hand, or a contract changed without the client, fails.
 *
 * The contract is read from its sources, `docs/api/openapi.yaml`, which the generator bundles as
 * `make build-openapi` does: the test needs no bundle built before it. `make client-up-to-date`
 * holds the whole of `generated/`, the routes of the examples included, in the chain.
 */
import { readFileSync } from "node:fs";
import { pathToFileURL } from "node:url";

import openapiTS, { astToString, COMMENT_HEADER } from "openapi-typescript";
import { describe, expect, it } from "vitest";

const CONTRACT = pathToFileURL(`${import.meta.dirname}/../../../docs/api/openapi.yaml`);
const VERSIONED = `${import.meta.dirname}/generated/schema.d.ts`;

// The whole contract goes through the generator, which takes a second or two alone, and more when
// other suites share the machine.
describe("the generated client", { timeout: 60_000 }, () => {
  it("is the one the contract produces, without a change made by hand [WF-ARC-0060-A]", async () => {
    // What the command line of openapi-typescript writes, without a configuration of Redocly in
    // `frontend/`, where `make generate-client` runs it: its banner, then the types.
    const generated = `${COMMENT_HEADER}${astToString(await openapiTS(CONTRACT, { silent: true }))}`;

    const versioned = readFileSync(VERSIONED, "utf8");
    expect(versioned.startsWith(COMMENT_HEADER)).toBe(true);
    expect(versioned).toBe(generated);
  });
});
