// SPDX-FileCopyrightText: 2026 waterfall-project
// SPDX-License-Identifier: AGPL-3.0-only
import { describe, expect, it } from "vitest";

import { HOME_LIST, homeQuery } from "./home-list";

describe("what the list of the home reads of its address", () => {
  it("holds every parameter the list asks of the server, but its page: a filter under way reads another list", () => {
    const query = homeQuery({
      filtered: true,
      states: ["pricing"],
      query: { sort: { column: "code", order: "desc" }, search: "poste" },
      offset: 50,
    });
    const asked = Object.keys(query).filter((name) => name !== HOME_LIST.page);
    expect(asked).toHaveLength(5);
    expect(HOME_LIST.reads).toEqual(expect.arrayContaining(asked));
  });

  it("asks every state when the address names none", () => {
    const query = homeQuery({
      filtered: false,
      states: [],
      query: { sort: undefined, search: undefined },
      offset: undefined,
    });
    expect(query).toEqual({
      states: ["created", "pricing", "in_progress", "completed", "lost", "abandoned"],
    });
  });
});
