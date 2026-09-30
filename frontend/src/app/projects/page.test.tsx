// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import ProjectsPage from "./page";

describe("the former address of the list of projects", () => {
  it("leads to the home, which is the list, on the server", () => {
    let thrown: unknown;
    try {
      ProjectsPage();
    } catch (error) {
      thrown = error;
    }
    expect(thrown).toMatchObject({ digest: expect.stringContaining(";/;") as unknown });
  });
});
