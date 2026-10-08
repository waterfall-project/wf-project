// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { homeStatesValue, isContributorFiltered, PROJECT_STATES, readHomeStates } from "./home";

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

describe("the states of the home", () => {
  it("reads the states of the address in the order of the contract, each once, an unknown one left", () => {
    expect(readHomeStates(new URLSearchParams("states=lost,pricing,lost,unknown"))).toEqual([
      "pricing",
      "lost",
    ]);
  });

  it("writes none for no state, and none for every state, which « Every state » shows", () => {
    expect(homeStatesValue([])).toBeUndefined();
    expect(homeStatesValue(PROJECT_STATES)).toBeUndefined();
    expect(homeStatesValue(["lost", "created"])).toBe("created,lost");
  });
});
