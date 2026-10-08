// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { isContributorFiltered } from "./home";

describe("the filter of the home", () => {
  it.each([
    ["", true],
    ["is_contributor=true", true],
    ["is_contributor=false", false],
  ])(
    "at the address ?%s, filters on the projects the user contributes to: %s",
    (query, filtered) => {
      expect(isContributorFiltered(new URLSearchParams(query))).toBe(filtered);
    },
  );
});
