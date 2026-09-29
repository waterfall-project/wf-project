// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import HomePage from "./page";

describe("the home page", () => {
  it("leads to the list of projects, on the server", () => {
    let thrown: unknown;
    try {
      HomePage();
    } catch (error) {
      thrown = error;
    }
    expect(thrown).toMatchObject({ digest: expect.stringContaining(";/projects;") as unknown });
  });
});
