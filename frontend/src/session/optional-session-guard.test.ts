// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
/*
 * The reads that go without a session cookie (`serverClient({ session: "optional" })`) are those of
 * the shell and no other: a screen that asked for it would not lead to the sign-in page when it has
 * no session (WF-SEC-0020, #2914). The option appears in these two modules alone.
 */
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import { describe, expect, it } from "vitest";

const SRC = join(import.meta.dirname, "..");
const ALLOWED = ["i18n/request.ts", "session/request.ts"];

/** The source files that are not tests, nor the module that defines the option. */
function sources(): string[] {
  return readdirSync(SRC, { recursive: true, encoding: "utf8" })
    .filter((file) => /\.tsx?$/.test(file) && !/\.test\.tsx?$/.test(file))
    .filter((file) => file !== "api/server.ts" && !file.startsWith("api/generated/"));
}

describe("the reads without a session (WF-SEC-0020, #2914)", () => {
  it("are asked for by the account of the layout and the language alone", () => {
    const asking = sources().filter((file) =>
      /session:\s*["']optional["']/.test(readFileSync(join(SRC, file), "utf8")),
    );
    expect(asking.sort()).toEqual(ALLOWED);
  });
});
